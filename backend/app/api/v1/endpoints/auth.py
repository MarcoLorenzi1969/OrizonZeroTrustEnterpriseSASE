"""
Orizon Zero Trust Connect - Auth Endpoints
For: Marco @ Syneto/Orizon
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.user import (
    LoginRequest,
    Token,
    UserResponse,
    UserCreate,
    RefreshTokenRequest,
)
from app.services.user_service import UserService
from app.auth.dependencies import get_current_user
from app.auth.security import decode_token, verify_token_type
from app.models.user import User
from loguru import logger

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    login_data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Login with email and password
    
    Returns JWT access and refresh tokens
    """
    # Get client IP
    client_ip = request.client.host if request.client else None
    
    # Authenticate user
    user = await UserService.authenticate_user(
        db,
        login_data.email,
        login_data.password,
        client_ip
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create tokens
    tokens = await UserService.create_tokens(user)
    
    logger.info(f"🔐 User logged in: {user.username} from {client_ip}")
    
    return tokens


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    # Decode refresh token
    payload = decode_token(refresh_data.refresh_token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    
    # Verify token type
    if not verify_token_type(payload, "refresh"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )
    
    # Get user
    user_id = payload.get("sub")
    user = await UserService.get_user_by_id(db, user_id)
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    
    # Create new tokens
    tokens = await UserService.create_tokens(user)
    
    return tokens


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user info
    """
    return current_user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_create: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register new user (self-registration)
    
    Creates a USER role by default
    """
    # Force USER role for self-registration
    user_create.role = User.Role.USER if hasattr(User, 'Role') else "user"
    
    # Create user
    user = await UserService.create_user(db, user_create)
    
    logger.info(f"📝 New user registered: {user.username}")
    
    return user


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """
    Logout current user
    
    Note: In a stateless JWT system, logout is handled client-side
    by discarding the token. This endpoint is for logging purposes.
    """
    logger.info(f"👋 User logged out: {current_user.username}")
    
    return {"message": "Successfully logged out"}
