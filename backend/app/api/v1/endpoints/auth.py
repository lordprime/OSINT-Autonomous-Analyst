"""
Authentication API
User registration, login, token management
"""

from fast api import APIRouter, HTTPException, status, Depends
from datetime import datetime, timedelta
from jose import jwt
import uuid

from app.schemas.requests import UserRegister, UserLogin, TokenRefresh
from app.schemas.responses import UserResponse, LoginResponse
from app.schemas.base import User, Token, TokenData
from app.core.config import settings
from app.core.security import hash_password, verify_password

router = APIRouter(tags=["auth"])

# In-memory user store for MVP (replace with database in production)
USERS_DB: dict[str, dict] = {}


def create_access_token(data: dict, expires_delta: timedelta = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(data: UserRegister):
    """
    Register new user
    
    Creates user account with hashed password
    """
    
    # Check if username exists
    if data.username in USERS_DB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email exists
    for user in USERS_DB.values():
        if user["email"] == data.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # Create user
    user_id = str(uuid.uuid4())
    hashed_pw = hash_password(data.password)
    
    user_data = {
        "id": user_id,
        "username": data.username,
        "email": data.email,
        "hashed_password": hashed_pw,
        "role": data.role,
        "created_at": datetime.utcnow(),
        "is_active": True
    }
    
    USERS_DB[data.username] = user_data
    
    user = User(
        id=user_id,
        username=data.username,
        email=data.email,
        role=data.role,
        created_at=user_data["created_at"],
        is_active=True
    )
    
    return UserResponse(user=user)


@router.post("/login", response_model=LoginResponse)
async def login(data: UserLogin):
    """
    Login and get JWT token
    
    Returns access token for authentication
    """
    
    user_data = USERS_DB.get(data.username)
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_password(data.password, user_data["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user_data["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": data.username, "role": user_data["role"]},
        expires_delta=access_token_expires
    )
    
    # Update last login
    user_data["last_login"] = datetime.utcnow()
    
    user = User(
        id=user_data["id"],
        username=user_data["username"],
        email=user_data["email"],
        role=user_data["role"],
        created_at=user_data["created_at"],
        last_login=user_data["last_login"],
        is_active=user_data["is_active"]
    )
    
    token = Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    
    return LoginResponse(token=token, user=user)


@router.post("/refresh", response_model=Token)
async def refresh_token(data: TokenRefresh):
    """
    Refresh access token
    
    (Simplified implementation - in production use refresh token rotation)
    """
    
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Token refresh not yet implemented"
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: TokenData = Depends(lambda: TokenData(username="demo", role="analyst"))):
    """Get current user information"""
    
    user_data = USERS_DB.get(current_user.username)
    
    if not user_data:
        # Return demo user if not found
        return UserResponse(user=User(
            id="demo",
            username=current_user.username,
            email="demo@example.com",
            role=current_user.role,
            created_at=datetime.utcnow(),
            is_active=True
        ))
    
    user = User(
        id=user_data["id"],
        username=user_data["username"],
        email=user_data["email"],
        role=user_data["role"],
        created_at=user_data["created_at"],
        last_login=user_data.get("last_login"),
        is_active=user_data["is_active"]
    )
    
    return UserResponse(user=user)


@router.post("/logout", response_model=dict)
async def logout():
    """
    Logout (client-side token deletion)
    
    In production, add token to blacklist
    """
    return {"message": "Logged out successfully. Delete token on client side."}
