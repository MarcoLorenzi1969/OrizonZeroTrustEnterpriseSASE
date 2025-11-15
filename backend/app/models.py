"""
Database Models for Orizon Zero Trust Connect
"""
from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, Text, JSON, Enum, Float, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import uuid
import enum

# Enum for User Roles
class UserRole(str, enum.Enum):
    SUPERUSER = "SUPERUSER"
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    USER = "USER"

# Enum for Node Status
class NodeStatus(str, enum.Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    CONNECTING = "CONNECTING"
    ERROR = "ERROR"
    MAINTENANCE = "MAINTENANCE"

# Enum for Tunnel Type
class TunnelType(str, enum.Enum):
    SSH = "SSH"
    HTTPS = "HTTPS"
    BOTH = "BOTH"

# Many-to-Many relationship for User-Groups
user_groups = Table(
    'user_groups',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE')),
    Column('group_id', UUID(as_uuid=True), ForeignKey('groups.id', ondelete='CASCADE'))
)

# Many-to-Many relationship for Node-Rules
node_rules = Table(
    'node_rules',
    Base.metadata,
    Column('node_id', UUID(as_uuid=True), ForeignKey('nodes.id', ondelete='CASCADE')),
    Column('rule_id', UUID(as_uuid=True), ForeignKey('access_rules.id', ondelete='CASCADE'))
)

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(255))
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Hierarchical relationship
    parent_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    parent = relationship("User", remote_side=[id], backref="children")
    
    # Company/Organization info
    company_name = Column(String(255))
    company_id = Column(String(100))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # Relationships
    nodes = relationship("Node", back_populates="owner", cascade="all, delete-orphan")
    groups = relationship("Group", secondary=user_groups, back_populates="users")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")

class Node(Base):
    __tablename__ = "nodes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hostname = Column(String(255), nullable=False)
    ip_address = Column(String(45), nullable=False)
    mac_address = Column(String(17))
    os_type = Column(String(50))  # Linux, Windows, macOS
    os_version = Column(String(100))
    
    # Node identification
    node_key = Column(String(255), unique=True, nullable=False)
    node_secret = Column(String(255), nullable=False)
    
    # Status and connectivity
    status = Column(Enum(NodeStatus), default=NodeStatus.OFFLINE)
    tunnel_type = Column(Enum(TunnelType), default=TunnelType.BOTH)
    last_seen = Column(DateTime(timezone=True))
    
    # SSH Tunnel info
    ssh_port = Column(Integer)
    ssh_local_port = Column(Integer)
    ssh_active = Column(Boolean, default=False)
    
    # HTTPS Tunnel info
    https_port = Column(Integer)
    https_local_port = Column(Integer)
    https_active = Column(Boolean, default=False)
    
    # Performance metrics
    cpu_usage = Column(Float)
    memory_usage = Column(Float)
    disk_usage = Column(Float)
    network_in = Column(Float)
    network_out = Column(Float)
    
    # Location (for visualization)
    latitude = Column(Float)
    longitude = Column(Float)
    city = Column(String(100))
    country = Column(String(100))
    
    # Metadata
    tags = Column(JSON, default=list)
    metadata = Column(JSON, default=dict)
    
    # Ownership
    owner_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    owner = relationship("User", back_populates="nodes")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    rules = relationship("AccessRule", secondary=node_rules, back_populates="nodes")
    connections = relationship("Connection", back_populates="node", cascade="all, delete-orphan")
    metrics = relationship("NodeMetric", back_populates="node", cascade="all, delete-orphan")

class Group(Base):
    __tablename__ = "groups"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    
    # Group settings
    max_nodes = Column(Integer, default=10)
    max_users = Column(Integer, default=5)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    users = relationship("User", secondary=user_groups, back_populates="groups")

class AccessRule(Base):
    __tablename__ = "access_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # Rule definition
    source_ip = Column(String(45))  # Can be CIDR
    destination_ip = Column(String(45))  # Can be CIDR
    protocol = Column(String(20))  # TCP, UDP, ICMP, ALL
    port_from = Column(Integer)
    port_to = Column(Integer)
    action = Column(String(20), default="ALLOW")  # ALLOW, DENY
    
    # Priority (lower number = higher priority)
    priority = Column(Integer, default=1000)
    
    # Active status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    nodes = relationship("Node", secondary=node_rules, back_populates="rules")

class Connection(Base):
    __tablename__ = "connections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Connection details
    connection_type = Column(Enum(TunnelType))
    local_port = Column(Integer)
    remote_port = Column(Integer)
    bytes_in = Column(Integer, default=0)
    bytes_out = Column(Integer, default=0)
    
    # Session info
    session_id = Column(String(255), unique=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True))
    duration = Column(Integer)  # in seconds
    
    # Node relationship
    node_id = Column(UUID(as_uuid=True), ForeignKey('nodes.id', ondelete='CASCADE'), nullable=False)
    node = relationship("Node", back_populates="connections")

class NodeMetric(Base):
    __tablename__ = "node_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Metrics
    cpu_percent = Column(Float)
    memory_percent = Column(Float)
    disk_percent = Column(Float)
    network_in_bytes = Column(Integer)
    network_out_bytes = Column(Integer)
    active_connections = Column(Integer)
    
    # Timestamp
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Node relationship
    node_id = Column(UUID(as_uuid=True), ForeignKey('nodes.id', ondelete='CASCADE'), nullable=False)
    node = relationship("Node", back_populates="metrics")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Log details
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50))
    resource_id = Column(String(255))
    ip_address = Column(String(45))
    user_agent = Column(Text)
    
    # Result
    status = Column(String(20))  # SUCCESS, FAILURE
    error_message = Column(Text)
    
    # Additional data
    metadata = Column(JSON, default=dict)
    
    # Timestamp
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # User relationship
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    user = relationship("User", back_populates="audit_logs")

class APIKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Key details
    name = Column(String(100), nullable=False)
    key = Column(String(255), unique=True, nullable=False)
    secret_hash = Column(String(255), nullable=False)
    
    # Permissions
    permissions = Column(JSON, default=list)
    rate_limit = Column(Integer, default=1000)  # requests per hour
    
    # Validity
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True))
    
    # Usage tracking
    last_used = Column(DateTime(timezone=True))
    usage_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # User relationship
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    user = relationship("User", back_populates="api_keys")