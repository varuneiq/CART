from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
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

# Models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    price: float
    description: str
    image_url: str
    stock: int = 100
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CartItem(BaseModel):
    product_id: str
    name: str
    price: float
    image_url: str
    quantity: int

class Cart(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    items: List[CartItem] = []
    total: float = 0.0
    updated_at: datetime = Field(default_factory=datetime.utcnow)

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
        password_hash=hashed_password
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
    return {"id": current_user.id, "email": current_user.email, "name": current_user.name}

# Product Routes
@api_router.get("/products", response_model=List[Product])
async def get_products():
    products = await db.products.find().to_list(100)
    return [Product(**product) for product in products]

@api_router.post("/products", response_model=Product)
async def create_product(product: Product):
    await db.products.insert_one(product.dict())
    return product

# Initialize sample products
@api_router.post("/init/products")
async def initialize_products():
    sample_products = [
        {
            "id": str(uuid.uuid4()),
            "name": "Wireless Headphones",
            "price": 99.99,
            "description": "High-quality wireless headphones with noise cancellation",
            "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=300&h=300&fit=crop",
            "stock": 50,
            "created_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Smartphone",
            "price": 699.99,
            "description": "Latest model smartphone with advanced camera",
            "image_url": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=300&h=300&fit=crop",
            "stock": 30,
            "created_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Laptop Bag",
            "price": 49.99,
            "description": "Durable laptop bag with multiple compartments",
            "image_url": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=300&h=300&fit=crop",
            "stock": 25,
            "created_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Coffee Mug",
            "price": 19.99,
            "description": "Premium ceramic coffee mug",
            "image_url": "https://images.unsplash.com/photo-1514228742587-6b1558fcf93a?w=300&h=300&fit=crop",
            "stock": 100,
            "created_at": datetime.utcnow()
        }
    ]
    
    # Clear existing products
    await db.products.delete_many({})
    
    # Insert sample products
    await db.products.insert_many(sample_products)
    
    return {"message": "Sample products initialized successfully"}

# Cart Routes
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
            quantity=quantity
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
async def checkout(current_user: User = Depends(get_current_user)):
    cart = await db.carts.find_one({"user_id": current_user.id})
    if not cart or not cart.get("items"):
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    # Mock checkout - in real app, integrate with payment processor
    order_id = str(uuid.uuid4())
    
    # Clear cart after checkout
    await db.carts.update_one(
        {"user_id": current_user.id},
        {"$set": {"items": [], "total": 0.0, "updated_at": datetime.utcnow()}}
    )
    
    return {
        "order_id": order_id,
        "total": cart["total"],
        "message": "Order placed successfully! (Mock checkout)"
    }

# Basic routes
@api_router.get("/")
async def root():
    return {"message": "Cart Management System API"}

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