"""
Orizon Zero Trust Connect - User Schemas
For: Marco @ Syneto/Orizon
Pydantic schemas for User model
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator
from app.models.user import UserRole, UserStatus


# Base schemas
class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    full_name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating new user"""
    password: str = Field(..., min_length=8, max_length=100)
    role: UserRole = UserRole.USER
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserUpdate(BaseModel):
    """Schema for updating user"""
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    full_name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8, max_length=100)


class UserInDB(UserBase):
    """User schema with database fields"""
    id: str
    role: UserRole
    status: UserStatus
    created_by_id: Optional[str]
    can_create_users: bool
    can_manage_tunnels: bool
    can_view_logs: bool
    can_manage_nodes: bool
    is_active: bool
    is_email_verified: bool
    last_login: Optional[datetime]
    last_ip: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserResponse(UserBase):
    """User schema for API responses"""
    id: str
    role: UserRole
    status: UserStatus
    full_name: Optional[str]
    company: Optional[str]
    can_create_users: bool
    can_manage_tunnels: bool
    can_view_logs: bool
    can_manage_nodes: bool
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserList(BaseModel):
    """Schema for list of users"""
    users: List[UserResponse]
    total: int
    page: int
    page_size: int


# Authentication schemas
class Token(BaseModel):
    """JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """JWT token payload data"""
    user_id: str
    email: str
    role: UserRole


class LoginRequest(BaseModel):
    """Login request schema"""
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema"""
    refresh_token: str


class PasswordResetRequest(BaseModel):
    """Password reset request schema"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation schema"""
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)
    
    @validator('new_password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class ChangePasswordRequest(BaseModel):
    """Change password request schema"""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)
