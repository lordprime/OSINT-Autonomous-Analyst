"""
API Dependencies - Authentication and Authorization
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import BaseModel
from typing import Optional

from app.core.config import settings
from app.core.security import verify_password  # For login endpoints

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = "analyst"

async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    """
    Validate JWT and return current user.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        
        # In a real system, you would fetch user from DB here to check existence/active status
        # For this prototype, we decode role from token or default to analyst
        role: str = payload.get("role", "analyst")
        
        return TokenData(username=username, role=role)
        
    except JWTError:
        raise credentials_exception

async def get_current_admin(
    current_user: TokenData = Depends(get_current_user),
) -> TokenData:
    """Verify user has admin role"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user
