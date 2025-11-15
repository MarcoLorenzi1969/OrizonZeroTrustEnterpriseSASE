"""
Orizon Zero Trust Connect - Tunnel Schemas
For: Marco @ Syneto/Orizon
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.tunnel import TunnelType, TunnelStatus as TunnelStatusEnum


class TunnelBase(BaseModel):
    """Base tunnel schema"""
    name: str = Field(..., min_length=1, max_length=255)
    tunnel_type: TunnelType
    local_port: int = Field(..., ge=1, le=65535)
    remote_port: int = Field(..., ge=1, le=65535)


class TunnelCreate(TunnelBase):
    """Schema for creating new tunnel"""
    node_id: str
    hub_host: str
    hub_port: int = Field(..., ge=1, le=65535)
    auto_reconnect: bool = True


class TunnelUpdate(BaseModel):
    """Schema for updating tunnel"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    auto_reconnect: Optional[bool] = None
    reconnect_delay_seconds: Optional[int] = Field(None, ge=1, le=300)


class TunnelResponse(TunnelBase):
    """Tunnel schema for API responses"""
    id: str
    status: TunnelStatusEnum
    node_id: str
    hub_host: str
    hub_port: int
    bytes_sent: int
    bytes_received: int
    connection_count: int
    last_connected_at: Optional[datetime]
    last_heartbeat: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class TunnelList(BaseModel):
    """Schema for list of tunnels"""
    tunnels: List[TunnelResponse]
    total: int


# New schemas for TunnelService

class TunnelInfo(BaseModel):
    """Tunnel information returned after creation"""
    tunnel_id: str
    node_id: str
    tunnel_type: str  # "ssh" or "https"
    local_port: int
    remote_port: int
    status: str
    created_at: datetime


class TunnelStatus(BaseModel):
    """Current tunnel status"""
    tunnel_id: str
    node_id: str
    status: str
    connected_at: Optional[datetime] = None
    last_health_check: Optional[datetime] = None
    health_status: str  # "healthy" or "unhealthy"


class TunnelHealth(BaseModel):
    """Tunnel health check result"""
    tunnel_id: str
    node_id: str
    is_healthy: bool
    last_check: datetime
    latency_ms: int = 0
