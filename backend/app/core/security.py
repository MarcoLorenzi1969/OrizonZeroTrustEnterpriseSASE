"""
Authentication and Security Functions
"""
from typing import Optional, Union, List
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.database import get_db
from app.models import User, UserRole
from app.schemas import TokenPayload
import secrets
import hashlib

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against hashed"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(
    subject: Union[str, int],
    role: str,
    scopes: List[str] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "role": role,
        "scopes": scopes or []
    }
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(
    subject: Union[str, int],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT refresh token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "refresh"
    }
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[TokenPayload]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return TokenPayload(**payload)
    except JWTError:
        return None

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_data = verify_token(token)
    if token_data is None:
        raise credentials_exception
    
    # Get user from database
    result = await db.execute(
        select(User).where(User.id == token_data.sub)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Role-based permission checks
class PermissionChecker:
    """Permission checker for hierarchical roles"""
    
    def __init__(self, allowed_roles: List[UserRole] = None):
        self.allowed_roles = allowed_roles or []
    
    async def __call__(self, user: User = Depends(get_current_active_user)) -> User:
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return user

# Permission dependencies
require_superuser = PermissionChecker([UserRole.SUPERUSER])
require_super_admin = PermissionChecker([UserRole.SUPERUSER, UserRole.SUPER_ADMIN])
require_admin = PermissionChecker([UserRole.SUPERUSER, UserRole.SUPER_ADMIN, UserRole.ADMIN])

async def check_user_hierarchy(
    acting_user: User,
    target_user: User,
    db: AsyncSession
) -> bool:
    """
    Check if acting_user has permission to modify target_user
    based on hierarchical structure
    """
    # Superuser can modify anyone
    if acting_user.role == UserRole.SUPERUSER:
        return True
    
    # Super Admin can modify Admins and Users under them
    if acting_user.role == UserRole.SUPER_ADMIN:
        if target_user.role in [UserRole.ADMIN, UserRole.USER]:
            # Check if target is in their hierarchy
            return await is_user_in_hierarchy(acting_user.id, target_user.id, db)
    
    # Admin can modify Users under them
    if acting_user.role == UserRole.ADMIN:
        if target_user.role == UserRole.USER:
            return await is_user_in_hierarchy(acting_user.id, target_user.id, db)
    
    # Users can only modify themselves
    if acting_user.role == UserRole.USER:
        return acting_user.id == target_user.id
    
    return False

async def is_user_in_hierarchy(
    parent_id: str,
    target_id: str,
    db: AsyncSession,
    max_depth: int = 10
) -> bool:
    """
    Check if target user is in the hierarchy of parent user
    """
    current_id = target_id
    depth = 0
    
    while current_id and depth < max_depth:
        # Get user's parent
        result = await db.execute(
            select(User.parent_id).where(User.id == current_id)
        )
        parent = result.scalar_one_or_none()
        
        if parent == parent_id:
            return True
        
        current_id = parent
        depth += 1
    
    return False

def generate_api_key() -> tuple[str, str]:
    """Generate API key and secret"""
    key = f"otc_{secrets.token_urlsafe(32)}"
    secret = secrets.token_urlsafe(48)
    secret_hash = hashlib.sha256(secret.encode()).hexdigest()
    return key, secret, secret_hash

def verify_api_key(secret: str, secret_hash: str) -> bool:
    """Verify API key secret"""
    return hashlib.sha256(secret.encode()).hexdigest() == secret_hash

def generate_node_credentials() -> tuple[str, str]:
    """Generate node key and secret"""
    node_key = f"node_{secrets.token_urlsafe(24)}"
    node_secret = secrets.token_urlsafe(32)
    return node_key, node_secret