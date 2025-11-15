"""
Orizon Zero Trust Connect - Tunnel Models
For: Marco @ Syneto/Orizon
SSH and HTTPS reverse tunnels
"""

from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base


class TunnelType(str, enum.Enum):
    """Tunnel protocol type"""
    SSH = "ssh"
    HTTPS = "https"


class TunnelStatus(str, enum.Enum):
    """Tunnel connection status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    CONNECTING = "connecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class Tunnel(Base):
    """SSH or HTTPS reverse tunnel"""
    
    __tablename__ = "tunnels"
    
    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    
    # Tunnel configuration
    tunnel_type = Column(Enum(TunnelType), nullable=False)
    status = Column(Enum(TunnelStatus), default=TunnelStatus.INACTIVE, nullable=False)
    
    # Port configuration
    local_port = Column(Integer, nullable=False)  # Port on node
    remote_port = Column(Integer, nullable=False)  # Port on hub
    
    # Hub connection details
    hub_host = Column(String(255), nullable=False)
    hub_port = Column(Integer, nullable=False)
    
    # Authentication
    ssh_key_fingerprint = Column(String(255), nullable=True)  # For SSH tunnels
    certificate_fingerprint = Column(String(255), nullable=True)  # For HTTPS tunnels
    
    # Connection metrics
    bytes_sent = Column(Integer, default=0)
    bytes_received = Column(Integer, default=0)
    connection_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    last_error = Column(String(500), nullable=True)
    
    # Health
    last_connected_at = Column(DateTime, nullable=True)
    last_disconnected_at = Column(DateTime, nullable=True)
    last_heartbeat = Column(DateTime, nullable=True)
    
    # Auto-reconnect settings
    auto_reconnect = Column(Boolean, default=True)
    reconnect_delay_seconds = Column(Integer, default=5)
    max_reconnect_attempts = Column(Integer, default=10)
    current_reconnect_attempt = Column(Integer, default=0)
    
    # Metadata
    tags = Column(JSON, default=list)
    metadata = Column(JSON, default=dict)
    
    # Ownership
    node_id = Column(String(36), ForeignKey("nodes.id"), nullable=False)
    node = relationship("Node", back_populates="tunnels")
    
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="tunnels")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Tunnel {self.name} ({self.tunnel_type}) - {self.status}>"
    
    @property
    def is_active(self) -> bool:
        """Check if tunnel is active"""
        return self.status == TunnelStatus.ACTIVE
    
    @property
    def connection_string(self) -> str:
        """Get connection string for tunnel"""
        if self.tunnel_type == TunnelType.SSH:
            return f"ssh://localhost:{self.remote_port}"
        elif self.tunnel_type == TunnelType.HTTPS:
            return f"https://localhost:{self.remote_port}"
        return ""
    
    @property
    def uptime_seconds(self) -> int:
        """Calculate tunnel uptime"""
        if not self.last_connected_at:
            return 0
        if self.status != TunnelStatus.ACTIVE:
            if self.last_disconnected_at:
                delta = self.last_disconnected_at - self.last_connected_at
                return int(delta.total_seconds())
            return 0
        delta = datetime.utcnow() - self.last_connected_at
        return int(delta.total_seconds())
