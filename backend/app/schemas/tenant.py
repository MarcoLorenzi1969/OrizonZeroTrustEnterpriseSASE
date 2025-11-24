"""
Orizon Zero Trust - Tenant Schemas
Pydantic schemas per validazione API tenant
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import re


# ============================================================================
# TENANT SCHEMAS
# ============================================================================

class TenantBase(BaseModel):
    """Base schema per Tenant"""
    name: str = Field(..., min_length=3, max_length=100, description="Nome unico tenant")
    display_name: str = Field(..., min_length=3, max_length=255, description="Nome visualizzato")
    description: Optional[str] = Field(None, max_length=1000, description="Descrizione tenant")
    company_info: Dict[str, Any] = Field(default_factory=dict, description="Informazioni azienda")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Configurazione tenant")
    quota: Dict[str, Any] = Field(default_factory=dict, description="Quote e limiti")

    @validator('name')
    def validate_name(cls, v):
        """Valida nome tenant - solo lowercase, numeri, underscore, trattini"""
        if not re.match(r'^[a-z0-9_-]+$', v):
            raise ValueError('Nome tenant deve contenere solo lowercase, numeri, underscore e trattini')
        return v


class TenantCreate(TenantBase):
    """Schema per creazione tenant"""
    pass


class TenantUpdate(BaseModel):
    """Schema per aggiornamento tenant"""
    display_name: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    company_info: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None
    quota: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    is_suspended: Optional[bool] = None
    expires_at: Optional[datetime] = None


class TenantResponse(TenantBase):
    """Schema per risposta tenant"""
    id: str
    slug: str
    created_by_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    is_active: bool
    is_suspended: bool
    expires_at: Optional[datetime]

    # Statistiche calcolate
    total_nodes: Optional[int] = 0
    total_groups: Optional[int] = 0

    class Config:
        from_attributes = True


class TenantList(BaseModel):
    """Lista paginata di tenant"""
    tenants: List[TenantResponse]
    total: int
    offset: int
    limit: int


# ============================================================================
# GROUP-TENANT ASSOCIATION SCHEMAS
# ============================================================================

class GroupTenantCreate(BaseModel):
    """Schema per associare gruppo a tenant (tenant_id viene dal path)"""
    group_id: str = Field(..., description="ID del gruppo")
    permissions: Dict[str, Any] = Field(default_factory=dict, description="Permessi specifici")


class GroupTenantUpdate(BaseModel):
    """Schema per aggiornare associazione gruppo-tenant"""
    permissions: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class GroupTenantResponse(BaseModel):
    """Schema per risposta associazione gruppo-tenant"""
    id: str
    group_id: str
    tenant_id: str
    permissions: Dict[str, Any]
    added_by_id: Optional[str]
    added_at: datetime
    is_active: bool

    # Info aggiuntive
    group_name: Optional[str] = None
    tenant_name: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================================
# TENANT-NODE ASSOCIATION SCHEMAS
# ============================================================================

class TenantNodeCreate(BaseModel):
    """Schema per associare nodo a tenant (tenant_id viene dal path)"""
    node_id: str = Field(..., description="ID del nodo edge")
    node_config: Dict[str, Any] = Field(default_factory=dict, description="Configurazione nodo per questo tenant")


class TenantNodeUpdate(BaseModel):
    """Schema per aggiornare associazione tenant-nodo"""
    node_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class TenantNodeResponse(BaseModel):
    """Schema per risposta associazione tenant-nodo"""
    id: str
    tenant_id: str
    node_id: str
    node_config: Dict[str, Any]
    added_by_id: Optional[str]
    added_at: datetime
    is_active: bool

    # Info aggiuntive
    node_name: Optional[str] = None
    node_status: Optional[str] = None
    tenant_name: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================================
# TENANT STATISTICS SCHEMAS
# ============================================================================

class TenantStatistics(BaseModel):
    """Statistiche tenant"""
    tenant_id: str
    tenant_name: str

    # Contatori
    total_nodes: int = 0
    active_nodes: int = 0
    total_groups: int = 0
    total_users: int = 0  # Calcolato tramite gruppi

    # Utilizzo risorse
    bandwidth_used_gb: float = 0.0
    storage_used_gb: float = 0.0

    # Quote
    nodes_limit: Optional[int] = None
    users_limit: Optional[int] = None
    bandwidth_limit_gb: Optional[int] = None
    storage_limit_gb: Optional[int] = None

    # Percentuali utilizzo
    nodes_usage_percent: float = 0.0
    users_usage_percent: float = 0.0
    bandwidth_usage_percent: float = 0.0
    storage_usage_percent: float = 0.0
