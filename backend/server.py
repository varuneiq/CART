from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import hashlib
import jwt
from passlib.context import CryptContext
import re
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncio

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Settings
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Enhanced Models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    phone: Optional[str] = None
    address: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserProfile(BaseModel):
    name: str
    phone: Optional[str] = None
    address: Optional[str] = None

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    password_hash: str
    phone: Optional[str] = None
    address: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    price: float
    description: str
    image_url: str
    category: str
    stock: int = 100
    rating: float = 0.0
    reviews_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CartItem(BaseModel):
    product_id: str
    name: str
    price: float
    image_url: str
    quantity: int
    category: str

class Cart(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    items: List[CartItem] = []
    total: float = 0.0
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Order(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    user_name: str
    user_email: str
    items: List[CartItem]
    total: float
    status: str = "completed"
    order_date: datetime = Field(default_factory=datetime.utcnow)
    shipping_address: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

# Utility Functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_email: str = payload.get("sub")
        if user_email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await db.users.find_one({"email": user_email})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        
        return User(**user)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Auth Routes
@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserRegister):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        name=user_data.name,
        password_hash=hashed_password,
        phone=user_data.phone,
        address=user_data.address
    )
    
    await db.users.insert_one(user.dict())
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    user = await db.users.find_one({"email": user_data.email})
    if not user or not verify_password(user_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"]}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@api_router.get("/auth/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "phone": current_user.phone,
        "address": current_user.address,
        "created_at": current_user.created_at
    }

@api_router.put("/auth/profile")
async def update_profile(profile_data: UserProfile, current_user: User = Depends(get_current_user)):
    await db.users.update_one(
        {"id": current_user.id},
        {"$set": {
            "name": profile_data.name,
            "phone": profile_data.phone,
            "address": profile_data.address
        }}
    )
    return {"message": "Profile updated successfully"}

# Enhanced Product Routes
@api_router.get("/products")
async def get_products(
    search: Optional[str] = Query(None, description="Search products by name or description"),
    category: Optional[str] = Query(None, description="Filter by category"),
    min_price: Optional[float] = Query(None, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, description="Maximum price filter"),
    sort_by: Optional[str] = Query("name", description="Sort by: name, price, rating, created_at"),
    sort_order: Optional[str] = Query("asc", description="Sort order: asc, desc"),
    limit: Optional[int] = Query(50, description="Maximum number of products to return")
):
    # Build query filter
    query_filter = {}
    
    if search:
        query_filter["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]
    
    if category:
        query_filter["category"] = category
    
    if min_price is not None or max_price is not None:
        price_filter = {}
        if min_price is not None:
            price_filter["$gte"] = min_price
        if max_price is not None:
            price_filter["$lte"] = max_price
        query_filter["price"] = price_filter
    
    # Build sort criteria
    sort_direction = 1 if sort_order == "asc" else -1
    sort_criteria = [(sort_by, sort_direction)]
    
    products = await db.products.find(query_filter).sort(sort_criteria).limit(limit).to_list(limit)
    return [Product(**product) for product in products]

@api_router.get("/products/categories")
async def get_categories():
    categories = await db.products.distinct("category")
    return {"categories": categories}

@api_router.get("/products/search/suggestions")
async def get_search_suggestions(q: str = Query(..., min_length=2)):
    # Get product names that match the query for autocomplete
    products = await db.products.find({
        "name": {"$regex": f"^{q}", "$options": "i"}
    }).limit(10).to_list(10)
    
    suggestions = [product["name"] for product in products]
    return {"suggestions": suggestions}

@api_router.post("/products", response_model=Product)
async def create_product(product: Product):
    await db.products.insert_one(product.dict())
    return product

# Initialize enhanced biotech/lab products
@api_router.post("/init/products")
async def initialize_products():
    sample_products = [
        # Antibodies Category
        {
            "id": str(uuid.uuid4()),
            "name": "Enterokinase Antibody, mAb, Mouse",
            "price": 9379.00,  # ₹9,379 (was $113)
            "description": "Mouse Anti-Enterokinase Monoclonal Antibody recognizes EK in Western blots and ELISAs. Enterokinase is an intestinal enzyme responsible for initiating activation of pancreatic proteolytic proenzymes.",
            "image_url": "https://images.unsplash.com/photo-1576086213369-97a306d36557?w=300&h=300&fit=crop",
            "category": "Antibodies",
            "stock": 25,
            "rating": 4.7,
            "reviews_count": 89,
            "created_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Beta-Actin Antibody, Polyclonal",
            "price": 7387.00,  # ₹7,387 (was $89)
            "description": "Rabbit polyclonal antibody against Beta-Actin. Ideal loading control for Western blot applications. High specificity and sensitivity.",
            "image_url": "https://images.unsplash.com/photo-1576086213369-97a306d36557?w=300&h=300&fit=crop",
            "category": "Antibodies",
            "stock": 45,
            "rating": 4.8,
            "reviews_count": 156,
            "created_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "GAPDH Antibody, Mouse mAb",
            "price": 7885.00,  # ₹7,885 (was $95)
            "description": "Mouse monoclonal antibody against GAPDH. Commonly used housekeeping gene control for Western blot and immunofluorescence.",
            "image_url": "https://images.unsplash.com/photo-1576086213369-97a306d36557?w=300&h=300&fit=crop",
            "category": "Antibodies",
            "stock": 35,
            "rating": 4.6,
            "reviews_count": 203,
            "created_at": datetime.utcnow()
        },
        
        # Lab Equipment Category
        {
            "id": str(uuid.uuid4()),
            "name": "Digital Micropipette Set (0.5-10μL, 2-20μL, 20-200μL)",
            "price": 20335.00,  # ₹20,335 (was $245)
            "description": "High-precision digital micropipette set with LCD display. Includes three volume ranges for accurate liquid handling in molecular biology applications.",
            "image_url": "https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?w=300&h=300&fit=crop",
            "category": "Lab Equipment",
            "stock": 15,
            "rating": 4.9,
            "reviews_count": 67,
            "created_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "PCR Thermal Cycler, 96-Well",
            "price": 240617.00,  # ₹2,40,617 (was $2899)
            "description": "Advanced thermal cycler for PCR applications. Features rapid heating/cooling, gradient capability, and intuitive touchscreen interface.",
            "image_url": "https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?w=300&h=300&fit=crop",
            "category": "Lab Equipment",
            "stock": 5,
            "rating": 4.8,
            "reviews_count": 34,
            "created_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Benchtop Centrifuge, 15,000 RPM",
            "price": 107817.00,  # ₹1,07,817 (was $1299)
            "description": "Compact benchtop centrifuge with digital display. Accommodates various tube sizes from 0.2mL to 15mL. Quiet operation with safety lock.",
            "image_url": "https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?w=300&h=300&fit=crop",
            "category": "Lab Equipment",
            "stock": 8,
            "rating": 4.7,
            "reviews_count": 45,
            "created_at": datetime.utcnow()
        },
        
        # Reagents Category
        {
            "id": str(uuid.uuid4()),
            "name": "Taq DNA Polymerase (500 Units)",
            "price": 5561.00,  # ₹5,561 (was $67)
            "description": "High-quality Taq DNA polymerase for PCR amplification. Includes 10x buffer and MgCl2 solution. Suitable for routine PCR applications.",
            "image_url": "https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=300&h=300&fit=crop",
            "category": "Reagents",
            "stock": 60,
            "rating": 4.5,
            "reviews_count": 128,
            "created_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Protein Ladder, Pre-stained (10-250 kDa)",
            "price": 3735.00,  # ₹3,735 (was $45)
            "description": "Pre-stained protein molecular weight marker for SDS-PAGE and Western blot applications. Sharp bands with consistent migration.",
            "image_url": "https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=300&h=300&fit=crop",
            "category": "Reagents",
            "stock": 85,
            "rating": 4.6,
            "reviews_count": 94,
            "created_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "ELISA Kit - Human IL-6",
            "price": 15687.00,  # ₹15,687 (was $189)
            "description": "Quantitative sandwich ELISA kit for human Interleukin-6 detection. High sensitivity and specificity. Includes all necessary reagents.",
            "image_url": "https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=300&h=300&fit=crop",
            "category": "Reagents",
            "stock": 25,
            "rating": 4.7,
            "reviews_count": 76,
            "created_at": datetime.utcnow()
        },
        
        # Consumables Category
        {
            "id": str(uuid.uuid4()),
            "name": "Microcentrifuge Tubes, 1.5mL (1000 pack)",
            "price": 2407.00,  # ₹2,407 (was $29)
            "description": "Sterile, DNase/RNase-free microcentrifuge tubes. Graduated markings and secure-fit caps. Ideal for sample storage and centrifugation.",
            "image_url": "https://images.unsplash.com/photo-1551601651-09e1c1c96b7a?w=300&h=300&fit=crop",
            "category": "Consumables",
            "stock": 150,
            "rating": 4.4,
            "reviews_count": 234,
            "created_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "PCR Tubes, 0.2mL (500 pack)",
            "price": 2905.00,  # ₹2,905 (was $35)
            "description": "Ultra-thin wall PCR tubes for optimal heat transfer. Compatible with most thermal cyclers. Clear polypropylene construction.",
            "image_url": "https://images.unsplash.com/photo-1551601651-09e1c1c96b7a?w=300&h=300&fit=crop",
            "category": "Consumables",
            "stock": 200,
            "rating": 4.3,
            "reviews_count": 167,
            "created_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Nitrile Gloves, Powder-Free (100 pack)",
            "price": 1245.00,  # ₹1,245 (was $15)
            "description": "Chemical-resistant nitrile gloves. Powder-free and latex-free. Textured fingertips for improved grip. Size Large.",
            "image_url": "https://images.unsplash.com/photo-1551601651-09e1c1c96b7a?w=300&h=300&fit=crop",
            "category": "Consumables",
            "stock": 300,
            "rating": 4.2,
            "reviews_count": 445,
            "created_at": datetime.utcnow()
        },
        
        # Instruments Category
        {
            "id": str(uuid.uuid4()),
            "name": "Digital pH Meter with Calibration",
            "price": 14857.00,  # ₹14,857 (was $179)
            "description": "High-precision digital pH meter with automatic temperature compensation. Includes electrode, calibration buffers, and carrying case.",
            "image_url": "https://images.unsplash.com/photo-1518152006812-edab29b069ac?w=300&h=300&fit=crop",
            "category": "Instruments",
            "stock": 20,
            "rating": 4.6,
            "reviews_count": 89,
            "created_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Analytical Balance, 0.1mg Precision",
            "price": 120350.00,  # ₹1,20,350 (was $1450)
            "description": "High-precision analytical balance with 0.1mg readability. Internal calibration, draft shield, and RS232 connectivity.",
            "image_url": "https://images.unsplash.com/photo-1518152006812-edab29b069ac?w=300&h=300&fit=crop",
            "category": "Instruments",
            "stock": 6,
            "rating": 4.8,
            "reviews_count": 52,
            "created_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "UV-Vis Spectrophotometer",
            "price": 273817.00,  # ₹2,73,817 (was $3299)
            "description": "Compact UV-Visible spectrophotometer for nucleic acid and protein quantification. Wavelength range 190-1100nm with high accuracy.",
            "image_url": "https://images.unsplash.com/photo-1518152006812-edab29b069ac?w=300&h=300&fit=crop",
            "category": "Instruments",
            "stock": 3,
            "rating": 4.9,
            "reviews_count": 28,
            "created_at": datetime.utcnow()
        }
    ]
    
    # Clear existing products
    await db.products.delete_many({})
    
    # Insert sample products
    await db.products.insert_many(sample_products)
    
    return {"message": "Biotech/Laboratory products initialized successfully", "count": len(sample_products)}

# Enhanced Cart Routes
@api_router.get("/cart")
async def get_cart(current_user: User = Depends(get_current_user)):
    cart = await db.carts.find_one({"user_id": current_user.id})
    if not cart:
        # Create empty cart
        empty_cart = Cart(user_id=current_user.id)
        await db.carts.insert_one(empty_cart.dict())
        return empty_cart
    return Cart(**cart)

@api_router.post("/cart/add")
async def add_to_cart(
    product_id: str, 
    quantity: int = 1,
    current_user: User = Depends(get_current_user)
):
    # Get product details
    product = await db.products.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get or create cart
    cart = await db.carts.find_one({"user_id": current_user.id})
    if not cart:
        cart = Cart(user_id=current_user.id).dict()
        await db.carts.insert_one(cart)
    
    # Check if item already exists in cart
    item_exists = False
    for item in cart.get("items", []):
        if item["product_id"] == product_id:
            item["quantity"] += quantity
            item_exists = True
            break
    
    if not item_exists:
        new_item = CartItem(
            product_id=product_id,
            name=product["name"],
            price=product["price"],
            image_url=product["image_url"],
            quantity=quantity,
            category=product["category"]
        )
        cart["items"] = cart.get("items", []) + [new_item.dict()]
    
    # Calculate total
    total = sum(item["price"] * item["quantity"] for item in cart["items"])
    cart["total"] = total
    cart["updated_at"] = datetime.utcnow()
    
    # Update cart in database
    await db.carts.replace_one({"user_id": current_user.id}, cart)
    
    return Cart(**cart)

@api_router.put("/cart/update")
async def update_cart_item(
    product_id: str, 
    quantity: int,
    current_user: User = Depends(get_current_user)
):
    cart = await db.carts.find_one({"user_id": current_user.id})
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    # Update quantity
    for item in cart["items"]:
        if item["product_id"] == product_id:
            if quantity <= 0:
                cart["items"].remove(item)
            else:
                item["quantity"] = quantity
            break
    
    # Calculate total
    total = sum(item["price"] * item["quantity"] for item in cart["items"])
    cart["total"] = total
    cart["updated_at"] = datetime.utcnow()
    
    await db.carts.replace_one({"user_id": current_user.id}, cart)
    
    return Cart(**cart)

@api_router.delete("/cart/remove/{product_id}")
async def remove_from_cart(product_id: str, current_user: User = Depends(get_current_user)):
    cart = await db.carts.find_one({"user_id": current_user.id})
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    # Remove item
    cart["items"] = [item for item in cart["items"] if item["product_id"] != product_id]
    
    # Calculate total
    total = sum(item["price"] * item["quantity"] for item in cart["items"])
    cart["total"] = total
    cart["updated_at"] = datetime.utcnow()
    
    await db.carts.replace_one({"user_id": current_user.id}, cart)
    
    return Cart(**cart)

@api_router.post("/cart/checkout")
async def checkout(shipping_address: Optional[str] = None, current_user: User = Depends(get_current_user)):
    cart = await db.carts.find_one({"user_id": current_user.id})
    if not cart or not cart.get("items"):
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    # Create order record
    order = Order(
        user_id=current_user.id,
        user_name=current_user.name,
        user_email=current_user.email,
        items=cart["items"],
        total=cart["total"],
        shipping_address=shipping_address or current_user.address
    )
    
    # Save order to database
    await db.orders.insert_one(order.dict())
    
    # Clear cart after checkout
    await db.carts.update_one(
        {"user_id": current_user.id},
        {"$set": {"items": [], "total": 0.0, "updated_at": datetime.utcnow()}}
    )
    
    return {
        "order_id": order.id,
        "total": order.total,
        "message": "Order placed successfully!",
        "order_date": order.order_date
    }

# Order History Routes
@api_router.get("/orders")
async def get_order_history(current_user: User = Depends(get_current_user)):
    orders = await db.orders.find({"user_id": current_user.id}).sort("order_date", -1).to_list(100)
    return [Order(**order) for order in orders]

@api_router.get("/orders/{order_id}")
async def get_order_details(order_id: str, current_user: User = Depends(get_current_user)):
    order = await db.orders.find_one({"id": order_id, "user_id": current_user.id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return Order(**order)

# Analytics Routes (for admin or user insights)
@api_router.get("/analytics/user-stats")
async def get_user_stats(current_user: User = Depends(get_current_user)):
    # Get user's order statistics
    orders = await db.orders.find({"user_id": current_user.id}).to_list(100)
    
    if not orders:
        return {
            "total_orders": 0,
            "total_spent": 0.0,
            "favorite_category": None,
            "average_order_value": 0.0
        }
    
    total_orders = len(orders)
    total_spent = sum(order["total"] for order in orders)
    average_order_value = total_spent / total_orders if total_orders > 0 else 0
    
    # Calculate favorite category
    category_counts = {}
    for order in orders:
        for item in order["items"]:
            category = item["category"]
            category_counts[category] = category_counts.get(category, 0) + item["quantity"]
    
    favorite_category = max(category_counts.items(), key=lambda x: x[1])[0] if category_counts else None
    
    return {
        "total_orders": total_orders,
        "total_spent": round(total_spent, 2),
        "favorite_category": favorite_category,
        "average_order_value": round(average_order_value, 2)
    }

# Admin & Order Management Routes
@api_router.get("/admin/orders")
async def get_all_orders():
    """Admin endpoint to get all orders in the system"""
    orders = await db.orders.find().sort("order_date", -1).to_list(1000)
    return [Order(**order) for order in orders]

@api_router.get("/admin/orders/stats")
async def get_order_stats():
    """Get order statistics for admin dashboard"""
    total_orders = await db.orders.count_documents({})
    
    if total_orders == 0:
        return {
            "total_orders": 0,
            "total_revenue": 0.0,
            "pending_orders": 0,
            "completed_orders": 0
        }
    
    # Get all orders for calculations
    orders = await db.orders.find().to_list(1000)
    
    total_revenue = sum(order["total"] for order in orders)
    completed_orders = len([o for o in orders if o["status"] == "completed"])
    pending_orders = len([o for o in orders if o["status"] == "pending"])
    
    return {
        "total_orders": total_orders,
        "total_revenue": round(total_revenue, 2),
        "pending_orders": pending_orders,
        "completed_orders": completed_orders
    }

@api_router.put("/admin/orders/{order_id}/status")
async def update_order_status(order_id: str, status: str):
    """Update order status (admin only)"""
    result = await db.orders.update_one(
        {"id": order_id},
        {"$set": {"status": status}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {"message": f"Order status updated to {status}"}

# Fulfillment Routes
@api_router.get("/admin/fulfillment/queue")
async def get_fulfillment_queue():
    """Get orders that need to be fulfilled"""
    orders = await db.orders.find({"status": {"$in": ["completed", "processing"]}}).sort("order_date", 1).to_list(100)
    return [Order(**order) for order in orders]
@api_router.get("/")
async def root():
    return {"message": "Enhanced Cart Management System API"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()