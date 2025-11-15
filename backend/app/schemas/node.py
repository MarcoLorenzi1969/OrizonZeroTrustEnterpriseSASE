"""
Orizon Zero Trust Connect - Node Schemas
For: Marco @ Syneto/Orizon
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.node import NodeStatus, NodeType


class NodeBase(BaseModel):
    """Base node schema"""
    name: str = Field(..., min_length=1, max_length=255)
    hostname: str
    node_type: NodeType


class NodeCreate(NodeBase):
    """Schema for creating new node"""
    public_ip: Optional[str] = None
    private_ip: Optional[str] = None
    location: Optional[str] = None
    tags: List[str] = []


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
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    last_heartbeat: Optional[datetime]
    created_at: datetime
    
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
