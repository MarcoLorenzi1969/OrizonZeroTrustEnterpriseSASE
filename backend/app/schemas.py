"""
Pydantic Schemas for API Request/Response Validation
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from uuid import UUID
from app.models import UserRole, NodeStatus, TunnelType

# Base schemas
class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: Optional[datetime] = None

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    company_id: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.USER
    parent_id: Optional[UUID] = None

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None

class UserResponse(UserBase):
    id: UUID
    role: UserRole
    is_active: bool
    is_verified: bool
    parent_id: Optional[UUID] = None
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class UserWithChildren(UserResponse):
    children: List["UserResponse"] = []

# Authentication Schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: str
    exp: int
    role: str
    scopes: List[str] = []

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

# Node Schemas
class NodeBase(BaseModel):
    hostname: str
    ip_address: str
    mac_address: Optional[str] = None
    os_type: Optional[str] = None
    os_version: Optional[str] = None
    tunnel_type: TunnelType = TunnelType.BOTH
    tags: List[str] = []
    metadata: Dict[str, Any] = {}

class NodeCreate(NodeBase):
    pass

class NodeUpdate(BaseModel):
    hostname: Optional[str] = None
    status: Optional[NodeStatus] = None
    tunnel_type: Optional[TunnelType] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

class NodeResponse(NodeBase):
    id: UUID
    node_key: str
    status: NodeStatus
    last_seen: Optional[datetime] = None
    ssh_active: bool
    https_active: bool
    owner_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Metrics
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    disk_usage: Optional[float] = None
    
    # Location
    city: Optional[str] = None
    country: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class NodeWithMetrics(NodeResponse):
    metrics: List["NodeMetricResponse"] = []
    connections: List["ConnectionResponse"] = []

# Access Rule Schemas
class AccessRuleBase(BaseModel):
    name: str
    description: Optional[str] = None
    source_ip: Optional[str] = None
    destination_ip: Optional[str] = None
    protocol: str = "ALL"
    port_from: Optional[int] = Field(None, ge=1, le=65535)
    port_to: Optional[int] = Field(None, ge=1, le=65535)
    action: str = "ALLOW"
    priority: int = Field(1000, ge=1, le=10000)
    is_active: bool = True

class AccessRuleCreate(AccessRuleBase):
    node_ids: List[UUID] = []

class AccessRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    source_ip: Optional[str] = None
    destination_ip: Optional[str] = None
    protocol: Optional[str] = None
    port_from: Optional[int] = Field(None, ge=1, le=65535)
    port_to: Optional[int] = Field(None, ge=1, le=65535)
    action: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=10000)
    is_active: Optional[bool] = None

class AccessRuleResponse(AccessRuleBase):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

# Connection Schemas
class ConnectionResponse(BaseModel):
    id: UUID
    connection_type: TunnelType
    local_port: Optional[int] = None
    remote_port: Optional[int] = None
    bytes_in: int
    bytes_out: int
    session_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)

# Node Metric Schemas
class NodeMetricResponse(BaseModel):
    id: UUID
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_in_bytes: int
    network_out_bytes: int
    active_connections: int
    timestamp: datetime
    
    model_config = ConfigDict(from_attributes=True)

# Group Schemas
class GroupBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = None
    max_nodes: int = Field(10, ge=1)
    max_users: int = Field(5, ge=1)

class GroupCreate(GroupBase):
    user_ids: List[UUID] = []

class GroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = None
    max_nodes: Optional[int] = Field(None, ge=1)
    max_users: Optional[int] = Field(None, ge=1)

class GroupResponse(GroupBase):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    users: List[UserResponse] = []
    
    model_config = ConfigDict(from_attributes=True)

# API Key Schemas
class APIKeyCreate(BaseModel):
    name: str
    permissions: List[str] = []
    rate_limit: int = Field(1000, ge=1)
    expires_at: Optional[datetime] = None

class APIKeyResponse(BaseModel):
    id: UUID
    name: str
    key: str  # Only shown once on creation
    permissions: List[str]
    rate_limit: int
    is_active: bool
    expires_at: Optional[datetime] = None
    created_at: datetime
    last_used: Optional[datetime] = None
    usage_count: int
    
    model_config = ConfigDict(from_attributes=True)

# Audit Log Schemas
class AuditLogResponse(BaseModel):
    id: UUID
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}
    timestamp: datetime
    user_id: Optional[UUID] = None
    
    model_config = ConfigDict(from_attributes=True)

# Dashboard Statistics
class DashboardStats(BaseModel):
    total_nodes: int
    online_nodes: int
    offline_nodes: int
    total_users: int
    active_users: int
    total_connections: int
    active_connections: int
    total_rules: int
    active_rules: int
    total_bandwidth_in: int
    total_bandwidth_out: int

# WebSocket Messages
class WSMessage(BaseModel):
    type: str  # node_status, metric_update, connection_update, etc.
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class NodeStatusUpdate(BaseModel):
    node_id: UUID
    status: NodeStatus
    last_seen: datetime

class MetricUpdate(BaseModel):
    node_id: UUID
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_in: float
    network_out: float