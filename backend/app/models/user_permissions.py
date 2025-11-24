"""
Orizon Zero Trust - User Permissions Model
Modello per permessi granulari utenti su nodi e servizi
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Table, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class PermissionLevel(str, enum.Enum):
    """Livelli di permesso"""
    NO_ACCESS = "no_access"
    VIEW_ONLY = "view_only"
    CONNECT = "connect"
    FULL_CONTROL = "full_control"


class ServiceType(str, enum.Enum):
    """Tipi di servizi disponibili"""
    SSH = "ssh"
    RDP = "rdp"
    VNC = "vnc"
    HTTP = "http"
    HTTPS = "https"
    CUSTOM = "custom"


# Tabella associativa per permessi utente-nodo
user_node_permissions = Table(
    'user_node_permissions',
    Base.metadata,
    Column('id', String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
    Column('user_id', String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
    Column('node_id', String(36), ForeignKey('nodes.id', ondelete='CASCADE'), nullable=False),
    Column('permission_level', SQLEnum(PermissionLevel), nullable=False, default=PermissionLevel.VIEW_ONLY),
    Column('can_ssh', Boolean, default=False),
    Column('can_rdp', Boolean, default=False),
    Column('can_vnc', Boolean, default=False),
    Column('can_http', Boolean, default=False),
    Column('can_https', Boolean, default=False),
    Column('allowed_services', String(500), nullable=True),  # JSON list of custom services
    Column('ip_whitelist', String(500), nullable=True),  # JSON list of allowed IPs
    Column('time_restrictions', String(500), nullable=True),  # JSON schedule
    Column('granted_by', String(36), ForeignKey('users.id'), nullable=True),
    Column('granted_at', DateTime, default=datetime.utcnow),
    Column('expires_at', DateTime, nullable=True),
    Column('is_active', Boolean, default=True),
    Column('notes', String(500), nullable=True)
)


# Permessi a livello di gruppo
class GroupNodePermission(Base):
    """Permessi gruppo-nodo"""
    __tablename__ = "group_node_permissions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    group_id = Column(String(36), ForeignKey('user_groups.id', ondelete='CASCADE'), nullable=False)
    node_id = Column(String(36), ForeignKey('nodes.id', ondelete='CASCADE'), nullable=False)
    permission_level = Column(SQLEnum(PermissionLevel), nullable=False, default=PermissionLevel.VIEW_ONLY)
    can_ssh = Column(Boolean, default=False)
    can_rdp = Column(Boolean, default=False)
    can_vnc = Column(Boolean, default=False)
    can_http = Column(Boolean, default=False)
    can_https = Column(Boolean, default=False)
    allowed_services = Column(String(500), nullable=True)
    granted_by = Column(String(36), ForeignKey('users.id'), nullable=True)
    granted_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)


# Audit log per accessi
class AccessLog(Base):
    """Log degli accessi ai nodi"""
    __tablename__ = "access_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    node_id = Column(String(36), ForeignKey('nodes.id', ondelete='SET NULL'), nullable=True)
    service_type = Column(SQLEnum(ServiceType), nullable=False)
    action = Column(String(50), nullable=False)  # connect, disconnect, denied, error
    source_ip = Column(String(45), nullable=False)
    user_agent = Column(String(500), nullable=True)
    session_id = Column(String(100), nullable=True)
    tunnel_port = Column(String(10), nullable=True)
    success = Column(Boolean, default=True)
    error_message = Column(String(500), nullable=True)
    duration_seconds = Column(String(20), nullable=True)
    bytes_transferred = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    # Note: extra_metadata column removed as it doesn't exist in DB


# Sessioni attive tunnel
class TunnelSession(Base):
    """Sessioni attive di tunnel"""
    __tablename__ = "tunnel_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    node_id = Column(String(36), ForeignKey('nodes.id', ondelete='CASCADE'), nullable=False)
    service_type = Column(SQLEnum(ServiceType), nullable=False)
    tunnel_id = Column(String(100), unique=True, nullable=False, index=True)
    local_port = Column(String(10), nullable=False)
    remote_port = Column(String(10), nullable=False)
    source_ip = Column(String(45), nullable=False)
    status = Column(String(20), default="active")  # active, disconnected, error
    started_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    connection_metadata = Column(String(1000), nullable=True)  # JSON
