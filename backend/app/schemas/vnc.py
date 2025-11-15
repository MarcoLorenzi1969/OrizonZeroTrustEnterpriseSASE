"""
Orizon Zero Trust Connect - VNC Session Schemas
For: Marco @ Syneto/Orizon
Pydantic schemas for VNC session API requests/responses
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class VNCSessionStatusEnum(str, Enum):
    """VNC session status"""
    PENDING = "pending"
    CONNECTING = "connecting"
    ACTIVE = "active"
    DISCONNECTED = "disconnected"
    EXPIRED = "expired"
    ERROR = "error"
    TERMINATED = "terminated"


class VNCQualityEnum(str, Enum):
    """VNC quality presets"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    LOSSLESS = "lossless"


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class VNCSessionCreate(BaseModel):
    """
    Create new VNC session request

    Example:
        {
            "node_id": "uuid-of-edge-node",
            "name": "Desktop Access - Production Server",
            "description": "Remote desktop for maintenance",
            "quality": "medium",
            "screen_width": 1920,
            "screen_height": 1080,
            "view_only": false,
            "max_duration_seconds": 300
        }
    """
    node_id: str = Field(..., description="Target edge node UUID")
    name: str = Field(..., min_length=1, max_length=255, description="Session display name")
    description: Optional[str] = Field(None, max_length=500, description="Optional description")

    # VNC Configuration
    vnc_host: str = Field(default="localhost", description="VNC server host on edge (usually localhost)")
    vnc_port: int = Field(default=5900, ge=5900, le=5999, description="VNC server port on edge (5900-5999)")
    quality: VNCQualityEnum = Field(default=VNCQualityEnum.MEDIUM, description="Connection quality preset")

    # Display settings
    screen_width: int = Field(default=1920, ge=640, le=7680, description="Screen width in pixels")
    screen_height: int = Field(default=1080, ge=480, le=4320, description="Screen height in pixels")
    allow_resize: bool = Field(default=True, description="Allow client to resize screen")

    # Security
    view_only: bool = Field(default=False, description="Read-only mode (no keyboard/mouse input)")
    require_acl_validation: bool = Field(default=True, description="Enforce ACL rules")

    # Session timing
    max_duration_seconds: int = Field(
        default=300,
        ge=60,
        le=3600,
        description="Maximum session duration (60-3600 seconds, default 5 min)"
    )

    # Metadata
    tags: List[str] = Field(default_factory=list, description="Session tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")

    @validator('node_id')
    def validate_node_id(cls, v):
        """Validate node_id is not empty"""
        if not v or v.strip() == "":
            raise ValueError("node_id cannot be empty")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "node_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Production Server Desktop",
                "description": "Emergency maintenance access",
                "quality": "medium",
                "screen_width": 1920,
                "screen_height": 1080,
                "view_only": False,
                "max_duration_seconds": 300
            }
        }


class VNCSessionUpdate(BaseModel):
    """Update VNC session settings (limited fields)"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    quality: Optional[VNCQualityEnum] = None
    view_only: Optional[bool] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Updated Session Name",
                "quality": "high",
                "view_only": True
            }
        }


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class VNCSessionResponse(BaseModel):
    """
    VNC session response

    Includes WebSocket URL and session token for client connection
    """
    id: str
    name: str
    description: Optional[str]
    status: VNCSessionStatusEnum

    # Connection details
    tunnel_port: Optional[int] = Field(None, description="Allocated port on hub")
    websocket_path: Optional[str] = Field(None, description="WebSocket endpoint path")
    websocket_url: Optional[str] = Field(None, description="Full WebSocket URL with token")
    session_token: Optional[str] = Field(None, description="JWT for this session (expires with session)")

    # VNC config
    vnc_host: str
    vnc_port: int
    quality: VNCQualityEnum

    # Display
    screen_width: int
    screen_height: int
    allow_resize: bool

    # Security
    view_only: bool
    require_acl_validation: bool

    # Timing
    max_duration_seconds: int
    expires_at: Optional[datetime]
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    remaining_seconds: Optional[int] = Field(None, description="Seconds until expiration")
    uptime_seconds: Optional[int] = Field(None, description="Session uptime in seconds")

    # Metrics
    bytes_sent: int = 0
    bytes_received: int = 0
    frames_sent: int = 0
    latency_ms: Optional[int] = None

    # Health
    last_activity_at: Optional[datetime]
    last_error: Optional[str]
    error_count: int = 0

    # Client info
    client_ip: Optional[str]
    client_user_agent: Optional[str]

    # Relationships
    node_id: str
    user_id: str
    tunnel_id: Optional[str]

    # Metadata
    tags: List[str] = []
    metadata: Dict[str, Any] = {}

    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Production Server Desktop",
                "description": "Emergency maintenance",
                "status": "active",
                "tunnel_port": 12345,
                "websocket_path": "/api/v1/vnc/ws/550e8400-e29b-41d4-a716-446655440000",
                "websocket_url": "wss://hub.example.com/api/v1/vnc/ws/550e8400-e29b-41d4-a716-446655440000?token=eyJ...",
                "session_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "quality": "medium",
                "screen_width": 1920,
                "screen_height": 1080,
                "view_only": False,
                "max_duration_seconds": 300,
                "remaining_seconds": 245,
                "uptime_seconds": 55,
                "node_id": "node-uuid",
                "user_id": "user-uuid",
                "created_at": "2025-11-15T10:30:00Z"
            }
        }


class VNCSessionList(BaseModel):
    """List of VNC sessions with pagination"""
    total: int = Field(..., description="Total number of sessions")
    sessions: List[VNCSessionResponse] = Field(..., description="List of sessions")
    page: int = Field(default=1, description="Current page")
    page_size: int = Field(default=50, description="Items per page")

    class Config:
        json_schema_extra = {
            "example": {
                "total": 5,
                "sessions": [],
                "page": 1,
                "page_size": 50
            }
        }


class VNCSessionStats(BaseModel):
    """VNC session statistics"""
    total_sessions: int = Field(..., description="Total sessions created")
    active_sessions: int = Field(..., description="Currently active sessions")
    total_bytes_sent: int = Field(..., description="Total bytes sent across all sessions")
    total_bytes_received: int = Field(..., description="Total bytes received")
    total_frames_sent: int = Field(..., description="Total RFB frames sent")
    avg_latency_ms: Optional[float] = Field(None, description="Average latency across active sessions")
    sessions_by_status: Dict[str, int] = Field(..., description="Count of sessions by status")

    class Config:
        json_schema_extra = {
            "example": {
                "total_sessions": 150,
                "active_sessions": 3,
                "total_bytes_sent": 1073741824,
                "total_bytes_received": 52428800,
                "total_frames_sent": 45000,
                "avg_latency_ms": 18.5,
                "sessions_by_status": {
                    "active": 3,
                    "disconnected": 120,
                    "expired": 25,
                    "error": 2
                }
            }
        }


# ============================================================================
# WEBSOCKET MESSAGES
# ============================================================================

class VNCWebSocketMessage(BaseModel):
    """WebSocket message for VNC session events"""
    type: str = Field(..., description="Message type: connect, disconnect, error, metrics")
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "type": "metrics",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2025-11-15T10:35:00Z",
                "data": {
                    "bytes_sent": 1048576,
                    "bytes_received": 524288,
                    "frames_sent": 1200,
                    "latency_ms": 15
                }
            }
        }


# ============================================================================
# ERROR RESPONSES
# ============================================================================

class VNCSessionError(BaseModel):
    """VNC session error response"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    session_id: Optional[str] = Field(None, description="Session ID if applicable")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "TUNNEL_CREATION_FAILED",
                "message": "Failed to create VNC tunnel to edge node",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "details": {
                    "node_status": "offline",
                    "last_seen": "2025-11-15T09:00:00Z"
                }
            }
        }
