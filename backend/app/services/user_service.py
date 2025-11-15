"""
Orizon Zero Trust Connect - User Service
For: Marco @ Syneto/Orizon
Business logic for user management
"""

import uuid
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, or_
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from app.models.user import User, UserRole, UserStatus
from app.schemas.user import UserCreate, UserUpdate, Token
from app.auth.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
)
from app.core.config import settings
from loguru import logger


class UserService:
    """Service for user operations"""
    
    @staticmethod
    async def create_user(
        db: AsyncSession,
        user_create: UserCreate,
        created_by: Optional[User] = None
    ) -> User:
        """
        Create new user
        
        Args:
            db: Database session
            user_create: User creation data
            created_by: User creating this user (for hierarchy)
            
        Returns:
            Created user
            
        Raises:
            HTTPException: If email/username already exists
        """
        try:
            # Check if email already exists
            result = await db.execute(
                select(User).where(User.email == user_create.email)
            )
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            
            # Check if username already exists
            result = await db.execute(
                select(User).where(User.username == user_create.username)
            )
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
            
            # Create user
            user = User(
                id=str(uuid.uuid4()),
                email=user_create.email,
                username=user_create.username,
                hashed_password=get_password_hash(user_create.password),
                full_name=user_create.full_name,
                company=user_create.company,
                phone=user_create.phone,
                role=user_create.role,
                status=UserStatus.ACTIVE,
                created_by_id=created_by.id if created_by else None,
            )
            
            # Set permissions based on role
            if user.role == UserRole.SUPERUSER:
                user.can_create_users = True
                user.can_manage_nodes = True
                user.can_manage_tunnels = True
                user.can_view_logs = True
            elif user.role == UserRole.SUPER_ADMIN:
                user.can_create_users = True
                user.can_manage_nodes = True
                user.can_manage_tunnels = True
                user.can_view_logs = True
            elif user.role == UserRole.ADMIN:
                user.can_create_users = True
                user.can_manage_nodes = False
                user.can_manage_tunnels = True
                user.can_view_logs = True
            else:  # USER
                user.can_create_users = False
                user.can_manage_nodes = False
                user.can_manage_tunnels = True
                user.can_view_logs = False
            
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
            logger.info(f"✅ User created: {user.username} ({user.role})")
            return user
            
        except IntegrityError as e:
            await db.rollback()
            logger.error(f"❌ User creation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already exists"
            )
    
    @staticmethod
    async def authenticate_user(
        db: AsyncSession,
        email: str,
        password: str,
        ip_address: Optional[str] = None
    ) -> Optional[User]:
        """
        Authenticate user by email and password
        
        Args:
            db: Database session
            email: User email
            password: User password
            ip_address: Client IP address
            
        Returns:
            User if authentication successful, None otherwise
        """
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account temporarily locked due to too many failed attempts"
            )
        
        # Verify password
        if not verify_password(password, user.hashed_password):
            # Increment failed login attempts
            user.failed_login_attempts += 1
            
            # Lock account after 5 failed attempts
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.utcnow() + timedelta(minutes=30)
                logger.warning(f"⚠️ Account locked: {user.email}")
            
            await db.commit()
            return None
        
        # Reset failed attempts on successful login
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.utcnow()
        user.last_ip = ip_address
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"✅ User authenticated: {user.username}")
        return user
    
    @staticmethod
    async def create_tokens(user: User) -> Token:
        """
        Create access and refresh tokens for user
        
        Args:
            user: User to create tokens for
            
        Returns:
            Token pair (access + refresh)
        """
        token_data = {
            "sub": user.id,
            "email": user.email,
            "role": user.role.value,
        }
        
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
    
    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
        """Get user by ID"""
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """Get user by email"""
        result = await db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def list_users(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        role: Optional[UserRole] = None,
        status: Optional[UserStatus] = None,
    ) -> List[User]:
        """List users with filtering"""
        query = select(User)
        
        if role:
            query = query.where(User.role == role)
        if status:
            query = query.where(User.status == status)
        
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def update_user(
        db: AsyncSession,
        user_id: str,
        user_update: UserUpdate
    ) -> Optional[User]:
        """Update user"""
        user = await UserService.get_user_by_id(db, user_id)
        if not user:
            return None
        
        update_data = user_update.model_dump(exclude_unset=True)
        
        # Hash password if provided
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
        
        for field, value in update_data.items():
            setattr(user, field, value)
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"✅ User updated: {user.username}")
        return user
    
    @staticmethod
    async def delete_user(db: AsyncSession, user_id: str) -> bool:
        """Delete user"""
        result = await db.execute(
            delete(User).where(User.id == user_id)
        )
        await db.commit()
        
        if result.rowcount > 0:
            logger.info(f"✅ User deleted: {user_id}")
            return True
        return False
