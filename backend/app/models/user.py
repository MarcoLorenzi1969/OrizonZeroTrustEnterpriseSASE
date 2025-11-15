"""
Orizon Zero Trust Connect - User Models
For: Marco @ Syneto/Orizon
RBAC: SuperUser → Super Admin → Admin → User
"""

from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from app.core.database import Base


class UserRole(str, enum.Enum):
    """User roles hierarchy"""
    SUPERUSER = "superuser"  # Marco - Proprietario
    SUPER_ADMIN = "super_admin"  # Distributori
    ADMIN = "admin"  # Rivenditori
    USER = "user"  # Clienti finali


class UserStatus(str, enum.Enum):
    """User account status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class User(Base):
    """User model with hierarchical RBAC"""
    
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # Profile
    full_name = Column(String(255))
    company = Column(String(255))
    phone = Column(String(50))
    
    # RBAC
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.PENDING, nullable=False)
    
    # Hierarchy - parent user who created this user
    created_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_by = relationship("User", remote_side=[id], backref="created_users")
    
    # Permissions
    can_create_users = Column(Boolean, default=False)
    can_manage_tunnels = Column(Boolean, default=True)
    can_view_logs = Column(Boolean, default=True)
    can_manage_nodes = Column(Boolean, default=False)
    
    # Authentication
    is_active = Column(Boolean, default=True)
    is_email_verified = Column(Boolean, default=False)
    email_verification_token = Column(String(255), nullable=True)
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime, nullable=True)
    
    # Session tracking
    last_login = Column(DateTime, nullable=True)
    last_ip = Column(String(50), nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    nodes = relationship("Node", back_populates="owner", cascade="all, delete-orphan")
    tunnels = relationship("Tunnel", back_populates="owner", cascade="all, delete-orphan")
    vnc_sessions = relationship("VNCSession", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.username} ({self.role})>"
    
    @property
    def is_superuser(self) -> bool:
        """Check if user is superuser"""
        return self.role == UserRole.SUPERUSER
    
    @property
    def is_super_admin(self) -> bool:
        """Check if user is super admin or higher"""
        return self.role in [UserRole.SUPERUSER, UserRole.SUPER_ADMIN]
    
    @property
    def is_admin(self) -> bool:
        """Check if user is admin or higher"""
        return self.role in [UserRole.SUPERUSER, UserRole.SUPER_ADMIN, UserRole.ADMIN]
    
    def can_manage_user(self, target_user: "User") -> bool:
        """
        Check if this user can manage target user
        Hierarchy: SuperUser > Super Admin > Admin > User
        """
        role_hierarchy = {
            UserRole.SUPERUSER: 4,
            UserRole.SUPER_ADMIN: 3,
            UserRole.ADMIN: 2,
            UserRole.USER: 1,
        }
        return role_hierarchy.get(self.role, 0) > role_hierarchy.get(target_user.role, 0)
