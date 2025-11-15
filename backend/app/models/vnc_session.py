"""
Orizon Zero Trust Connect - VNC Session Models
For: Marco @ Syneto/Orizon
Secure Remote Desktop via noVNC + WebSocket + Zero Trust
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
from datetime import datetime, timedelta
import enum
from app.core.database import Base


class VNCSessionStatus(str, enum.Enum):
    """VNC session lifecycle status"""
    PENDING = "pending"          # Session created, waiting for tunnel
    CONNECTING = "connecting"    # Tunnel ready, client connecting
    ACTIVE = "active"           # Client connected and streaming
    DISCONNECTED = "disconnected"  # Client disconnected
    EXPIRED = "expired"         # Session token expired
    ERROR = "error"             # Error during setup/connection
    TERMINATED = "terminated"   # Manually terminated


class VNCQuality(str, enum.Enum):
    """VNC connection quality preset"""
    LOW = "low"           # 8-bit color, high compression (slow networks)
    MEDIUM = "medium"     # 16-bit color, medium compression
    HIGH = "high"         # 24-bit color, low compression (LAN)
    LOSSLESS = "lossless" # 32-bit color, no compression


class VNCSession(Base):
    """
    VNC Remote Desktop Session

    Zero Trust Architecture:
    1. Client (Browser) connects to WebSocket endpoint with JWT
    2. VNC Gateway validates JWT and proxies to tunnel port
    3. Tunnel port is reverse-connected from Edge Agent
    4. Edge Agent connects to localhost:5900 (VNC server)

    Security:
    - No VNC ports exposed to Internet
    - All connections originate from edge (Zero Trust)
    - JWT expires after max_duration (default 5 min)
    - RBAC + ACL validation before session creation
    - Full audit logging
    """

    __tablename__ = "vnc_sessions"

    # Primary key
    id = Column(String(36), primary_key=True, index=True)

    # Session metadata
    name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    status = Column(Enum(VNCSessionStatus), default=VNCSessionStatus.PENDING, nullable=False)

    # Connection details
    tunnel_port = Column(Integer, nullable=True)  # Allocated port on hub (e.g., 12345)
    websocket_path = Column(String(500), nullable=True)  # WS path: /api/v1/vnc/ws/{session_id}
    session_token = Column(String(1024), nullable=True)  # JWT for this session only

    # VNC configuration
    vnc_host = Column(String(255), default="localhost")  # VNC server on edge (usually localhost)
    vnc_port = Column(Integer, default=5900)  # VNC server port on edge
    quality = Column(Enum(VNCQuality), default=VNCQuality.MEDIUM)

    # Display settings
    screen_width = Column(Integer, default=1920)
    screen_height = Column(Integer, default=1080)
    allow_resize = Column(Boolean, default=True)

    # Security settings
    view_only = Column(Boolean, default=False)  # Read-only mode (no input)
    require_acl_validation = Column(Boolean, default=True)

    # Session timing
    max_duration_seconds = Column(Integer, default=300)  # 5 minutes default
    expires_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)

    # Connection metrics
    bytes_sent = Column(Integer, default=0)
    bytes_received = Column(Integer, default=0)
    frames_sent = Column(Integer, default=0)  # RFB frames
    latency_ms = Column(Integer, nullable=True)

    # Health
    last_activity_at = Column(DateTime, nullable=True)
    last_error = Column(String(500), nullable=True)
    error_count = Column(Integer, default=0)

    # Client information
    client_ip = Column(String(45), nullable=True)  # IPv4/IPv6
    client_user_agent = Column(String(500), nullable=True)

    # Metadata
    tags = Column(JSON, default=list)
    metadata = Column(JSON, default=dict)

    # Relationships - Foreign Keys
    node_id = Column(String(36), ForeignKey("nodes.id"), nullable=False)
    node = relationship("Node", back_populates="vnc_sessions")

    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="vnc_sessions")

    tunnel_id = Column(String(36), ForeignKey("tunnels.id"), nullable=True)
    tunnel = relationship("Tunnel")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<VNCSession {self.id} - {self.node.name if self.node else 'N/A'} ({self.status})>"

    @property
    def is_active(self) -> bool:
        """Check if session is currently active"""
        return self.status == VNCSessionStatus.ACTIVE

    @property
    def is_expired(self) -> bool:
        """Check if session has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def remaining_seconds(self) -> int:
        """Calculate remaining session time in seconds"""
        if not self.expires_at:
            return 0
        delta = self.expires_at - datetime.utcnow()
        return max(0, int(delta.total_seconds()))

    @property
    def uptime_seconds(self) -> int:
        """Calculate session uptime"""
        if not self.started_at:
            return 0
        if self.ended_at:
            delta = self.ended_at - self.started_at
        else:
            delta = datetime.utcnow() - self.started_at
        return int(delta.total_seconds())

    @property
    def websocket_url(self) -> str:
        """Get full WebSocket URL for client connection"""
        if not self.websocket_path:
            return ""
        # Will be constructed as: wss://hub-domain/api/v1/vnc/ws/{session_id}?token={jwt}
        return f"wss://{{HUB_DOMAIN}}{self.websocket_path}?token={self.session_token}"

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "tunnel_port": self.tunnel_port,
            "websocket_path": self.websocket_path,
            "quality": self.quality.value,
            "screen_width": self.screen_width,
            "screen_height": self.screen_height,
            "view_only": self.view_only,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "remaining_seconds": self.remaining_seconds,
            "uptime_seconds": self.uptime_seconds,
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "frames_sent": self.frames_sent,
            "latency_ms": self.latency_ms,
            "node_id": self.node_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
