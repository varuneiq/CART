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

# Initialize enhanced sample products
@api_router.post("/init/products")
async def initialize_products():
    sample_products = [
        # Electronics Category
        {
            "id": str(uuid.uuid4()),
            "name": "Wireless Bluetooth Headphones",
            "price": 99.99,
            "description": "Premium wireless headphones with active noise cancellation and 30-hour battery life",
            "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=300&h=300&fit=crop",
            "category": "Electronics",
            "stock": 50,
            "rating": 4.5,
            "reviews_count": 128,
            "created_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Smartphone Pro Max",
            "price": 699.99,
            "description": "Latest flagship smartphone with advanced camera system and 5G connectivity",
            "image_url": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=300&h=300&fit=crop",
            "category": "Electronics",
            "stock": 30,
            "rating": 4.8,
            "reviews_count": 256,
            "created_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Wireless Charging Pad",
            "price": 29.99,
            "description": "Fast wireless charging pad compatible with all Qi-enabled devices",
            "image_url": "https://images.unsplash.com/photo-1586953208448-b95a79798f07?w=300&h=300&fit=crop",
            "category": "Electronics",
            "stock": 75,
            "rating": 4.2,
            "reviews_count": 89,
            "created_at": datetime.utcnow()
        },
        
        # Fashion Category
        {
            "id": str(uuid.uuid4()),
            "name": "Premium Leather Handbag",
            "price": 149.99,
            "description": "Elegant leather handbag with multiple compartments and adjustable strap",
            "image_url": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=300&h=300&fit=crop",
            "category": "Fashion",
            "stock": 25,
            "rating": 4.6,
            "reviews_count": 67,
            "created_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Classic Denim Jacket",
            "price": 79.99,
            "description": "Timeless denim jacket made from premium cotton with vintage wash",
            "image_url": "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=300&h=300&fit=crop",
            "category": "Fashion",
            "stock": 40,
            "rating": 4.3,
            "reviews_count": 45,
            "created_at": datetime.utcnow()
        },
        
        # Home Category
        {
            "id": str(uuid.uuid4()),
            "name": "Ceramic Coffee Mug Set",
            "price": 34.99,
            "description": "Set of 4 premium ceramic coffee mugs with ergonomic handles",
            "image_url": "https://images.unsplash.com/photo-1514228742587-6b1558fcf93a?w=300&h=300&fit=crop",
            "category": "Home",
            "stock": 100,
            "rating": 4.7,
            "reviews_count": 156,
            "created_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Bamboo Cutting Board",
            "price": 24.99,
            "description": "Eco-friendly bamboo cutting board with juice groove and non-slip feet",
            "image_url": "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=300&h=300&fit=crop",
            "category": "Home",
            "stock": 60,
            "rating": 4.4,
            "reviews_count": 92,
            "created_at": datetime.utcnow()
        },
        
        # Sports Category
        {
            "id": str(uuid.uuid4()),
            "name": "Yoga Exercise Mat",
            "price": 39.99,
            "description": "Premium non-slip yoga mat with alignment guides and carrying strap",
            "image_url": "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=300&h=300&fit=crop",
            "category": "Sports",
            "stock": 45,
            "rating": 4.5,
            "reviews_count": 78,
            "created_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Stainless Steel Water Bottle",
            "price": 19.99,
            "description": "Insulated stainless steel water bottle keeps drinks cold for 24 hours",
            "image_url": "https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=300&h=300&fit=crop",
            "category": "Sports",
            "stock": 80,
            "rating": 4.6,
            "reviews_count": 134,
            "created_at": datetime.utcnow()
        }
    ]
    
    # Clear existing products
    await db.products.delete_many({})
    
    # Insert sample products
    await db.products.insert_many(sample_products)
    
    return {"message": "Enhanced sample products initialized successfully", "count": len(sample_products)}

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

# Basic routes
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