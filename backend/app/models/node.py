"""
Orizon Zero Trust Connect - Node Models
For: Marco @ Syneto/Orizon
Represents edge nodes in the network
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
    Float,
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base


class NodeStatus(str, enum.Enum):
    """Node connection status"""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"


class NodeType(str, enum.Enum):
    """Node type/platform"""
    LINUX = "linux"
    MACOS = "macos"
    WINDOWS = "windows"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"


class ReverseTunnelType(str, enum.Enum):
    """Reverse tunnel protocols"""
    SSH = "SSH"
    SSL = "SSL"


class ExposedApplication(str, enum.Enum):
    """Applications that can be exposed through reverse tunnel"""
    TERMINAL = "TERMINAL"
    RDP = "RDP"
    VNC = "VNC"
    WEB_SERVER = "WEB_SERVER"


class Node(Base):
    """Edge node in the network"""
    
    __tablename__ = "nodes"
    
    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    hostname = Column(String(255), nullable=False)
    
    # Node details
    node_type = Column(Enum(NodeType), nullable=False)
    status = Column(Enum(NodeStatus), default=NodeStatus.OFFLINE, nullable=False)
    
    # Network info
    public_ip = Column(String(50))
    private_ip = Column(String(50))
    mac_address = Column(String(50))
    
    # System info
    os_version = Column(String(255))
    kernel_version = Column(String(255))
    architecture = Column(String(50))
    cpu_cores = Column(Integer)
    memory_mb = Column(Integer)
    disk_gb = Column(Float)
    
    # Agent info
    agent_version = Column(String(50))
    agent_installed_at = Column(DateTime)
    agent_token = Column(String(255), unique=True, nullable=True, index=True)

    # SSH credentials for terminal access
    ssh_username = Column(String(100), nullable=True)
    ssh_password = Column(String(255), nullable=True)  # TODO: Encrypt in production

    # Reverse tunnel configuration
    reverse_tunnel_type = Column(
        String(20),
        default=ReverseTunnelType.SSH.value,
        nullable=False
    )
    exposed_applications = Column(JSON, default=list, nullable=False)
    application_ports = Column(JSON, default=dict, nullable=False)

    # Service tunnel for heartbeat/metrics (always active)
    service_tunnel_port = Column(Integer, nullable=True)  # Remote port on hub for service tunnel

    # Location (optional)
    location = Column(String(255))
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Tags and metadata
    tags = Column(JSON, default=list)
    custom_metadata = Column(JSON, default=dict)
    
    # Health metrics
    cpu_usage = Column(Float, default=0.0)
    memory_usage = Column(Float, default=0.0)
    disk_usage = Column(Float, default=0.0)
    last_heartbeat = Column(DateTime, nullable=True)

    # Hardening information (JSON for flexibility across OS types)
    hardening_firewall = Column(JSON, nullable=True)  # Firewall status and rules
    hardening_antivirus = Column(JSON, nullable=True)  # AV/Defender status
    hardening_open_ports = Column(JSON, nullable=True)  # List of listening ports
    hardening_security_modules = Column(JSON, nullable=True)  # SELinux/AppArmor/etc
    hardening_updates = Column(JSON, nullable=True)  # Security updates info
    hardening_ssh_config = Column(JSON, nullable=True)  # SSH hardening (Linux)
    hardening_ssl_info = Column(JSON, nullable=True)  # SSL/TLS configuration
    hardening_audit = Column(JSON, nullable=True)  # Audit logging status
    hardening_last_scan = Column(DateTime, nullable=True)  # Last hardening scan time
    
    # Ownership
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="nodes")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tunnels = relationship("Tunnel", back_populates="node", cascade="all, delete-orphan")
    rules = relationship(
        "AccessRule",
        back_populates="node",
        foreign_keys="[AccessRule.node_id]",
        cascade="all, delete-orphan"
    )
    audit_logs = relationship("AuditLog", back_populates="node")
    
    def __repr__(self):
        return f"<Node {self.name} ({self.status})>"
    
    @property
    def is_online(self) -> bool:
        """Check if node is online"""
        return self.status == NodeStatus.ONLINE
    
    @property
    def uptime_seconds(self) -> int:
        """Calculate uptime since last heartbeat"""
        if not self.last_heartbeat:
            return 0
        delta = datetime.utcnow() - self.last_heartbeat
        return int(delta.total_seconds())

    def get_default_ports_for_application(self, app: ExposedApplication) -> dict:
        """Get default local/remote ports for an application"""
        defaults = {
            ExposedApplication.TERMINAL: {"local": 22, "remote": None},
            ExposedApplication.RDP: {"local": 3389, "remote": None},
            ExposedApplication.VNC: {"local": 5900, "remote": None},
            ExposedApplication.WEB_SERVER: {"local": 80, "remote": None},
        }
        return defaults.get(app, {"local": None, "remote": None})
