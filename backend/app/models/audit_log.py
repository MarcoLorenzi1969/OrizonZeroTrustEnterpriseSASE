"""
Orizon Zero Trust Connect - Audit Log Model
SQLAlchemy model for security audit logging

Author: Marco Lorenzi - Syneto Orizon
"""

from sqlalchemy import Column, String, DateTime, Enum, Integer, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class AuditAction(str, enum.Enum):
    """Audit action types"""
    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGED = "password_changed"
    PASSWORD_RESET = "password_reset"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"
    
    # User Management
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    USER_SUSPENDED = "user_suspended"
    USER_ACTIVATED = "user_activated"
    
    # Node Management
    NODE_REGISTERED = "node_registered"
    NODE_UPDATED = "node_updated"
    NODE_DELETED = "node_deleted"
    NODE_CONNECTED = "node_connected"
    NODE_DISCONNECTED = "node_disconnected"
    
    # Tunnel Management
    TUNNEL_CREATED = "tunnel_created"
    TUNNEL_STARTED = "tunnel_started"
    TUNNEL_STOPPED = "tunnel_stopped"
    TUNNEL_DELETED = "tunnel_deleted"
    TUNNEL_ERROR = "tunnel_error"
    
    # Security Events
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    PERMISSION_DENIED = "permission_denied"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    
    # Configuration
    CONFIG_CHANGED = "config_changed"
    SETTING_CHANGED = "setting_changed"


class AuditSeverity(str, enum.Enum):
    """Audit severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditLog(Base):
    """Audit log model"""
    __tablename__ = "audit_logs"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Action
    action = Column(Enum(AuditAction), nullable=False, index=True)
    severity = Column(Enum(AuditSeverity), nullable=False, default=AuditSeverity.INFO)
    
    # Actor (who performed the action)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    user_email = Column(String(255), nullable=True)
    user_role = Column(String(50), nullable=True)
    
    # Target (what was affected)
    target_type = Column(String(50), nullable=True)  # user, node, tunnel, etc.
    target_id = Column(String(255), nullable=True, index=True)
    target_name = Column(String(255), nullable=True)
    
    # Node context (if applicable)
    node_id = Column(UUID(as_uuid=True), ForeignKey("nodes.id"), nullable=True, index=True)
    
    # Request information
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    request_method = Column(String(10), nullable=True)
    request_path = Column(String(500), nullable=True)
    
    # Details
    description = Column(Text, nullable=False)
    details = Column(JSONB, default={})
    
    # Changes (before/after for updates)
    changes = Column(JSONB, default={})
    
    # Response
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    
    # Geolocation
    country = Column(String(2), nullable=True)
    city = Column(String(100), nullable=True)
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    node = relationship("Node", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog {self.action} by {self.user_email} at {self.timestamp}>"
    
    def to_dict(self) -> dict:
        """Convert audit log to dictionary"""
        return {
            "id": str(self.id),
            "action": self.action.value,
            "severity": self.severity.value,
            "user_id": str(self.user_id) if self.user_id else None,
            "user_email": self.user_email,
            "user_role": self.user_role,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "target_name": self.target_name,
            "node_id": str(self.node_id) if self.node_id else None,
            "ip_address": str(self.ip_address) if self.ip_address else None,
            "user_agent": self.user_agent,
            "request_method": self.request_method,
            "request_path": self.request_path,
            "description": self.description,
            "details": self.details,
            "changes": self.changes,
            "success": self.success,
            "error_message": self.error_message,
            "country": self.country,
            "city": self.city,
            "timestamp": self.timestamp.isoformat(),
        }


# Helper function to create audit log
async def create_audit_log(
    db,
    action: AuditAction,
    user_id: uuid.UUID = None,
    user_email: str = None,
    description: str = "",
    target_type: str = None,
    target_id: str = None,
    target_name: str = None,
    details: dict = None,
    severity: AuditSeverity = AuditSeverity.INFO,
    success: bool = True,
    error_message: str = None,
    ip_address: str = None,
    user_agent: str = None,
    request_method: str = None,
    request_path: str = None,
):
    """Helper to create audit log entry"""
    log = AuditLog(
        action=action,
        severity=severity,
        user_id=user_id,
        user_email=user_email,
        description=description,
        target_type=target_type,
        target_id=str(target_id) if target_id else None,
        target_name=target_name,
        details=details or {},
        success=success,
        error_message=error_message,
        ip_address=ip_address,
        user_agent=user_agent,
        request_method=request_method,
        request_path=request_path,
    )
    
    db.add(log)
    await db.commit()
    
    return log
