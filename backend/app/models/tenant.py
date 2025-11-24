"""
Orizon Zero Trust Connect - Tenant Models
For: Marco @ Syneto/Orizon

Multi-Tenant System:
- Tenant: Organizzazione/Cliente isolato
- GroupTenant: Associazione Gruppo <-> Tenant (many-to-many)
- TenantNode: Associazione Tenant <-> Nodi Edge (many-to-many)

Gerarchia:
  Gruppi → possono accedere a più Tenant
  Tenant → possono avere più Edge Server (Nodi)
  Utenti → appartengono a Gruppi → accedono a Tenant → usano Nodi
"""

from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Text,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Tenant(Base):
    """
    Tenant = Organizzazione/Cliente isolato

    Ogni tenant rappresenta un'organizzazione separata con:
    - Propri edge server (nodi)
    - Propri utenti (tramite gruppi)
    - Isolamento completo dei dati
    """

    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Identificativo univoco per il tenant (slug-friendly)
    slug = Column(String(100), unique=True, nullable=False, index=True)

    # Informazioni organizzazione
    company_info = Column(JSON, default=dict, nullable=False)
    # {
    #   "company_name": "Acme Corp",
    #   "vat_number": "IT12345678901",
    #   "address": "...",
    #   "city": "...",
    #   "country": "IT",
    #   "contact_email": "...",
    #   "contact_phone": "..."
    # }

    # Configurazione tenant
    settings = Column(JSON, default=dict, nullable=False)
    # {
    #   "max_nodes": 100,
    #   "max_users": 50,
    #   "max_groups": 10,
    #   "features_enabled": ["ssh", "rdp", "vnc", "file_transfer"],
    #   "session_timeout_minutes": 30,
    #   "require_mfa": false,
    #   "allowed_ip_ranges": ["10.0.0.0/8"],
    #   "storage_quota_gb": 100
    # }

    # Limiti e quote
    quota = Column(JSON, default=dict, nullable=False)
    # {
    #   "nodes_limit": 100,
    #   "users_limit": 50,
    #   "bandwidth_gb_month": 1000,
    #   "storage_gb": 100
    # }

    # Creator e ownership (chi ha creato il tenant - tipicamente SUPER_ADMIN o SUPERUSER)
    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by = relationship("User", foreign_keys=[created_by_id])

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Soft delete e stato
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_suspended = Column(Boolean, default=False, nullable=False, index=True)

    # Data scadenza (per tenant a tempo)
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    group_associations = relationship("GroupTenant", back_populates="tenant", cascade="all, delete-orphan")
    node_associations = relationship("TenantNode", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Tenant(id={self.id}, name={self.name}, slug={self.slug})>"


class GroupTenant(Base):
    """
    Many-to-many: Gruppi <-> Tenant

    Un gruppo può accedere a più tenant
    Un tenant può essere accessibile da più gruppi
    """

    __tablename__ = "group_tenants"

    id = Column(String(36), primary_key=True, index=True)
    group_id = Column(String(36), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Permessi specifici del gruppo su questo tenant
    permissions = Column(JSON, default=dict, nullable=False)
    # {
    #   "can_create_nodes": true,
    #   "can_delete_nodes": false,
    #   "can_manage_users": false,
    #   "can_view_audit_logs": true,
    #   "max_concurrent_sessions": 10
    # }

    # Chi ha associato questo gruppo al tenant
    added_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    added_by = relationship("User", foreign_keys=[added_by_id])

    # Timestamp
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Stato attivo
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    group = relationship("Group", backref="tenant_associations")
    tenant = relationship("Tenant", back_populates="group_associations")

    def __repr__(self):
        return f"<GroupTenant(group_id={self.group_id}, tenant_id={self.tenant_id})>"


class TenantNode(Base):
    """
    Many-to-many: Tenant <-> Nodi Edge

    Un tenant può avere più edge server
    Un nodo può appartenere a più tenant (condivisione risorse)
    """

    __tablename__ = "tenant_nodes"

    id = Column(String(36), primary_key=True, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    node_id = Column(String(36), ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False, index=True)

    # Configurazione specifica per questo nodo in questo tenant
    node_config = Column(JSON, default=dict, nullable=False)
    # {
    #   "node_alias": "Web Server Prod",  // Nome custom per questo tenant
    #   "enabled_services": ["ssh", "http", "https"],
    #   "custom_ports": {"ssh": 2222, "http": 8080},
    #   "resource_limits": {
    #     "max_cpu_percent": 80,
    #     "max_memory_mb": 4096,
    #     "max_disk_gb": 100
    #   }
    # }

    # Chi ha associato questo nodo al tenant
    added_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    added_by = relationship("User", foreign_keys=[added_by_id])

    # Timestamp
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Stato attivo
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="node_associations")
    node = relationship("Node", backref="tenant_associations")

    def __repr__(self):
        return f"<TenantNode(tenant_id={self.tenant_id}, node_id={self.node_id})>"
