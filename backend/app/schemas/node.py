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

    # Service tunnel (heartbeat/metrics)
    service_tunnel_port: Optional[int] = None

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


# === Heartbeat and Metrics Schemas ===

class HeartbeatRequest(BaseModel):
    """Heartbeat request from agent"""
    agent_token: str
    timestamp: Optional[datetime] = None
    agent_version: Optional[str] = None
    os_version: Optional[str] = None
    kernel_version: Optional[str] = None
    uptime_seconds: Optional[int] = None


class HeartbeatResponse(BaseModel):
    """Heartbeat response to agent"""
    status: str = "ok"
    server_time: datetime
    next_heartbeat_seconds: int = 30
    commands: List[Dict[str, Any]] = []  # Commands for agent to execute


class NodeMetricsUpdate(BaseModel):
    """Metrics update from agent"""
    agent_token: str
    cpu_usage: float = Field(..., ge=0, le=100)
    memory_usage: float = Field(..., ge=0, le=100)
    disk_usage: float = Field(..., ge=0, le=100)
    cpu_cores: Optional[int] = None
    memory_mb: Optional[int] = None
    disk_gb: Optional[float] = None
    network_rx_bytes: Optional[int] = None
    network_tx_bytes: Optional[int] = None
    active_connections: Optional[int] = None
    timestamp: Optional[datetime] = None


class NodeMetricsResponse(BaseModel):
    """Response after metrics update"""
    status: str = "ok"
    received_at: datetime


class ServiceTunnelConfig(BaseModel):
    """Configuration for the service tunnel (heartbeat/metrics)"""
    hub_host: str
    hub_ssh_port: int = 2222
    service_port: int  # Remote port on hub for this node's service tunnel
    heartbeat_interval: int = 30
    metrics_interval: int = 60
