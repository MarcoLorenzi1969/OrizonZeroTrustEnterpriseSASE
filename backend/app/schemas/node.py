"""
Orizon Zero Trust Connect - Node Schemas
For: Marco @ Syneto/Orizon
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum
from app.models.node import NodeStatus, NodeType, ReverseTunnelType, ExposedApplication


# Re-export enums for schema use
class ReverseTunnelTypeEnum(str, Enum):
    SSH = "SSH"
    SSL = "SSL"


class ExposedApplicationEnum(str, Enum):
    TERMINAL = "TERMINAL"
    RDP = "RDP"
    VNC = "VNC"
    WEB_SERVER = "WEB_SERVER"


class ApplicationPortConfig(BaseModel):
    """Port configuration for an application"""
    local: int = Field(..., ge=1, le=65535, description="Local port on the node")
    remote: Optional[int] = Field(None, ge=1, le=65535, description="Remote port on hub (auto-assigned if None)")


class NodeBase(BaseModel):
    """Base node schema"""
    name: str = Field(..., min_length=1, max_length=255)
    hostname: str
    node_type: NodeType


class NodeCreate(NodeBase):
    """Schema for creating new node with reverse tunnel configuration"""
    public_ip: Optional[str] = None
    private_ip: Optional[str] = None
    location: Optional[str] = None
    tags: List[str] = []

    # Reverse tunnel configuration
    reverse_tunnel_type: ReverseTunnelTypeEnum = ReverseTunnelTypeEnum.SSH
    exposed_applications: List[ExposedApplicationEnum] = Field(
        default_factory=list,
        description="Applications to expose through reverse tunnel"
    )
    application_ports: Optional[Dict[str, ApplicationPortConfig]] = Field(
        default_factory=dict,
        description="Custom port mappings (optional, uses defaults if not provided)"
    )

    @validator('exposed_applications')
    def validate_applications(cls, v):
        if not v:
            raise ValueError("At least one application must be exposed")
        if len(v) != len(set(v)):
            raise ValueError("Duplicate applications not allowed")
        return v


class NodeUpdate(BaseModel):
    """Schema for updating node"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[NodeStatus] = None
    location: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class NodeMetrics(BaseModel):
    """Node health metrics"""
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    timestamp: datetime


class NodeResponse(NodeBase):
    """Node schema for API responses"""
    id: str
    status: NodeStatus
    public_ip: Optional[str]
    private_ip: Optional[str]
    os_version: Optional[str]
    agent_version: Optional[str]
    agent_token: Optional[str]
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    last_heartbeat: Optional[datetime]
    created_at: datetime

    # Reverse tunnel configuration
    reverse_tunnel_type: str
    exposed_applications: List[str]
    application_ports: Dict[str, dict]

    class Config:
        from_attributes = True


class NodeList(BaseModel):
    """Schema for list of nodes"""
    nodes: List[NodeResponse]
    total: int


# === Provisioning Schemas ===

class ServiceConfig(BaseModel):
    """Service configuration for provisioning"""
    name: str
    port: int
    protocol: str = "tcp"
    enabled: bool = True


class ProvisionRequest(BaseModel):
    """Request to provision a node"""
    node_id: str
    services: List[ServiceConfig] = []


class ProvisionData(BaseModel):
    """Provisioning data with QR code and scripts"""
    node_id: str
    provision_token: str
    provision_url: str
    qr_code_data_url: str  # Base64 PNG data URL
    download_urls: Dict[str, str]  # {os_type: download_url}
    services: List[ServiceConfig]
    expires_at: datetime


class ScriptDownloadRequest(BaseModel):
    """Request to download provision script"""
    node_id: str
    os_type: str  # linux, macos, windows
    token: str
