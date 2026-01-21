from fastapi import APIRouter, HTTPException, Body, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
import bcrypt
import jwt
import logging
from datetime import datetime, timedelta
import os

from core.mongodb import get_mongodb, convert_id_to_str, str_to_objectid
from core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()

# JWT Secret
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DAYS = 7

# Pydantic models for request/response
class RegisterRequest(BaseModel):
    fullName: str
    email: str  # Changed from EmailStr to str for more flexibility
    password: str
    role: Optional[str] = "bid_manager"
    
    class Config:
        # Allow extra fields to be ignored
        extra = "forbid"

class LoginRequest(BaseModel):
    email: str  # Changed from EmailStr to str for more flexibility
    password: str

class UserResponse(BaseModel):
    id: str  # Changed to string for MongoDB ObjectId
    fullName: str
    email: str
    role: str

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_jwt_token(user_id: str, email: str, role: str) -> str:
    """Create a JWT token for a user"""
    payload = {
        "userId": str(user_id),  # Convert to string for MongoDB ObjectId
        "email": email,
        "role": role,
        "exp": datetime.utcnow() + timedelta(days=JWT_EXPIRATION_DAYS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_jwt_token(token: str) -> dict:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Dependency to get current user from JWT token"""
    token = credentials.credentials
    payload = verify_jwt_token(token)
    
    db = get_mongodb()
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        user_id = str_to_objectid(payload["userId"])
        if not user_id:
            raise HTTPException(status_code=404, detail="Invalid user ID")
        
        user = db.users.find_one({"_id": user_id})
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "id": str(user["_id"]),
            "fullName": user["full_name"],
            "email": user["email"],
            "role": user.get("role", "bid_manager")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")

@router.post("/register")
async def register(request: RegisterRequest):
    """Register a new user"""
    try:
        # Validation
        if not request.fullName or not request.fullName.strip():
            raise HTTPException(
                status_code=400,
                detail="Full name is required"
            )
        
        if not request.email or not request.email.strip():
            raise HTTPException(
                status_code=400,
                detail="Email is required"
            )
        
        # Basic email validation
        email = request.email.strip().lower()
        if "@" not in email or "." not in email.split("@")[1]:
            raise HTTPException(
                status_code=400,
                detail="Please enter a valid email address"
            )
        
        if not request.password or len(request.password) < 6:
            raise HTTPException(
                status_code=400,
                detail="Password must be at least 6 characters long"
            )
        
        db = get_mongodb()
        if db is None:
            logger.error("❌ Database connection failed")
            raise HTTPException(
                status_code=500, 
                detail="Database connection failed. Please check your MongoDB server."
            )
        
        try:
            users_collection = db.users
            
            # Check if user already exists
            existing_user = users_collection.find_one({"email": email})
            
            if existing_user:
                raise HTTPException(
                    status_code=400,
                    detail="User with this email already exists"
                )
            
            # Hash password
            hashed_password = hash_password(request.password)
            
            # Create user document
            user_doc = {
                "full_name": request.fullName.strip(),
                "email": email,
                "password": hashed_password,
                "role": request.role or "bid_manager",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Insert user
            result = users_collection.insert_one(user_doc)
            user_id = str(result.inserted_id)
            
            # Create unique index on email
            users_collection.create_index("email", unique=True)
            
            # Generate JWT token
            token = create_jwt_token(user_id, email, user_doc["role"])
            
            logger.info(f"✅ User registered: {email}")
            
            return {
                "success": True,
                "message": "User registered successfully",
                "token": token,
                "user": {
                    "id": user_id,
                    "fullName": user_doc["full_name"],
                    "email": email,
                    "role": user_doc["role"]
                }
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Registration error: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Internal server error during registration: {str(e)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during registration: {str(e)}"
        )

@router.post("/login")
async def login(request: LoginRequest):
    """Login user"""
    try:
        db = get_mongodb()
        if db is None:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        try:
            users_collection = db.users
            
            # Find user by email
            user = users_collection.find_one({"email": request.email.strip().lower()})
            
            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid email or password"
                )
            
            user_id = str(user["_id"])
            full_name = user["full_name"]
            email = user["email"]
            hashed_password = user["password"]
            role = user.get("role", "bid_manager")
            
            # Verify password
            if not verify_password(request.password, hashed_password):
                raise HTTPException(
                    status_code=401,
                    detail="Invalid email or password"
                )
            
            # Generate JWT token
            token = create_jwt_token(user_id, email, role)
            
            logger.info(f"✅ User logged in: {email}")
            
            return {
                "success": True,
                "message": "Login successful",
                "token": token,
                "user": {
                    "id": user_id,
                    "fullName": full_name,
                    "email": email,
                    "role": role
                }
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Internal server error during login"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during login"
        )

@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user info"""
    return {
        "success": True,
        "user": current_user
    }

@router.post("/logout")
async def logout():
    """Logout user (client-side token removal)"""
    return {
        "success": True,
        "message": "Logout successful"
    }

@router.get("/test")
async def test_auth():
    """Test endpoint to verify auth routes are working"""
    # Test database connection
    db = get_mongodb()
    db_status = "connected" if db is not None else "failed"
    
    if db is not None:
        try:
            # Check if users collection exists
            collections = db.list_collection_names()
            users_exists = "users" in collections
            
            # Get user count
            user_count = db.users.count_documents({}) if users_exists else 0
            
            return {
                "success": True,
                "message": "Auth routes are working!",
                "database": db_status,
                "database_type": "MongoDB",
                "users_collection_exists": users_exists,
                "user_count": user_count,
                "endpoints": {
                    "register": "POST /api/auth/register",
                    "login": "POST /api/auth/login",
                    "me": "GET /api/auth/me",
                    "logout": "POST /api/auth/logout"
                }
            }
        except Exception as e:
            return {
                "success": True,
                "message": "Auth routes are working!",
                "database": db_status,
                "database_type": "MongoDB",
                "error": str(e),
                "endpoints": {
                    "register": "POST /api/auth/register",
                    "login": "POST /api/auth/login",
                    "me": "GET /api/auth/me",
                    "logout": "POST /api/auth/logout"
                }
            }
    
    return {
        "success": True,
        "message": "Auth routes are working!",
        "database": db_status,
        "database_type": "MongoDB",
        "warning": "Database connection failed - check your MongoDB settings",
        "endpoints": {
            "register": "POST /api/auth/register",
            "login": "POST /api/auth/login",
            "me": "GET /api/auth/me",
            "logout": "POST /api/auth/logout"
        }
    }

