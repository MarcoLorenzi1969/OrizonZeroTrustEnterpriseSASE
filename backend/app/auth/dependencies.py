"""
Orizon Zero Trust Connect - Auth Dependencies
For: Marco @ Syneto/Orizon
FastAPI dependencies for authentication and authorization
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import User, UserRole
from app.auth.security import decode_token, verify_token_type, check_permission
from app.schemas.user import TokenData

# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token
    
    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Decode token
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload is None:
        raise credentials_exception
    
    # Verify token type
    if not verify_token_type(payload, "access"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )
    
    # Extract user ID
    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    # Get user from database
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


# Role-based access control dependencies
class RoleChecker:
    """Dependency for checking user role"""
    
    def __init__(self, required_role: UserRole):
        self.required_role = required_role
    
    async def __call__(
        self,
        current_user: User = Depends(get_current_user)
    ) -> User:
        """Check if user has required role"""
        if not check_permission(current_user.role, self.required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {self.required_role.value}",
            )
        return current_user


# Specific role dependencies
require_superuser = RoleChecker(UserRole.SUPERUSER)
require_super_admin = RoleChecker(UserRole.SUPER_ADMIN)
require_admin = RoleChecker(UserRole.ADMIN)
require_user = RoleChecker(UserRole.USER)


# Flexible role checker function
def require_role(roles):
    """
    Create role checker dependency for single role or list of roles

    Args:
        roles: UserRole or list of UserRole values

    Returns:
        RoleChecker dependency
    """
    if isinstance(roles, list):
        # For multiple roles, accept any of them
        async def check_any_role(current_user: User = Depends(get_current_user)) -> User:
            for role in roles:
                if check_permission(current_user.role, role):
                    return current_user
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required one of: {[r.value for r in roles]}",
            )
        return check_any_role
    else:
        # Single role
        return RoleChecker(roles)


# Permission checkers
async def can_create_users(
    current_user: User = Depends(get_current_user)
) -> User:
    """Check if user can create other users"""
    if not current_user.can_create_users:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to create users",
        )
    return current_user


async def can_manage_nodes(
    current_user: User = Depends(get_current_user)
) -> User:
    """Check if user can manage nodes"""
    if not current_user.can_manage_nodes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage nodes",
        )
    return current_user


async def can_manage_tunnels(
    current_user: User = Depends(get_current_user)
) -> User:
    """Check if user can manage tunnels"""
    if not current_user.can_manage_tunnels:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage tunnels",
        )
    return current_user


async def can_view_logs(
    current_user: User = Depends(get_current_user)
) -> User:
    """Check if user can view logs"""
    if not current_user.can_view_logs:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view logs",
        )
    return current_user
