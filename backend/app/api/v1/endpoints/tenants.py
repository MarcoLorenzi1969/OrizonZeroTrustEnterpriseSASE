"""
Orizon Zero Trust - Tenants Endpoints
API completa per gestione tenant multi-tenant
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import uuid4

from app.core.database import get_db
from app.auth.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.tenant import Tenant, GroupTenant, TenantNode
from app.schemas.tenant import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantList,
    GroupTenantCreate,
    GroupTenantResponse,
    TenantNodeCreate,
    TenantNodeResponse,
    TenantStatistics
)
from app.services.tenant_service import TenantService
from loguru import logger

router = APIRouter()


# ============================================================================
# TENANT CRUD
# ============================================================================

@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_data: TenantCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN))
):
    """
    Crea nuovo tenant

    Richiede ruolo: SUPER_ADMIN o superiore
    """
    try:
        tenant = await TenantService.create_tenant(
            db=db,
            name=tenant_data.name,
            display_name=tenant_data.display_name,
            created_by=current_user,
            description=tenant_data.description,
            company_info=tenant_data.company_info,
            settings=tenant_data.settings,
            quota=tenant_data.quota
        )

        logger.info(f"📦 Tenant created: {tenant.name} (ID: {tenant.id}) by {current_user.email}")

        return tenant

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=TenantList)
async def list_tenants(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    include_inactive: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lista tutti i tenant accessibili all'utente

    Visibilità:
    - SUPERUSER: tutti i tenant
    - SUPER_ADMIN/ADMIN: tenant creati da loro e subordinati
    - USER: tenant accessibili tramite gruppi
    """
    tenants = await TenantService.get_all_tenants(
        db, current_user, skip=skip, limit=limit, include_inactive=include_inactive
    )

    # Conta totale (senza paginazione)
    all_tenants = await TenantService.get_all_tenants(
        db, current_user, skip=0, limit=10000, include_inactive=include_inactive
    )
    total = len(all_tenants)

    logger.info(f"📋 User {current_user.email} listed {len(tenants)}/{total} tenants")

    return TenantList(tenants=tenants, total=total, offset=skip, limit=limit)


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ottieni tenant per ID

    Richiede accesso al tenant
    """
    # Verifica accesso
    can_access = await TenantService.can_user_access_tenant(db, current_user, tenant_id)
    if not can_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Non autorizzato ad accedere a questo tenant"
        )

    tenant = await TenantService.get_tenant_by_id(db, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant non trovato"
        )

    return tenant


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    tenant_data: TenantUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN))
):
    """
    Aggiorna tenant

    Richiede ruolo: SUPER_ADMIN o superiore
    """
    tenant = await TenantService.get_tenant_by_id(db, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant non trovato"
        )

    # Aggiorna campi
    update_data = tenant_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tenant, field, value)

    await db.commit()
    await db.refresh(tenant)

    logger.info(f"📝 Tenant updated: {tenant.name} (ID: {tenant_id})")

    return tenant


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SUPERUSER))
):
    """
    Elimina tenant (soft delete)

    Richiede ruolo: SUPERUSER
    """
    tenant = await TenantService.get_tenant_by_id(db, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant non trovato"
        )

    # Soft delete
    tenant.is_active = False
    await db.commit()

    logger.info(f"🗑️  Tenant deleted (soft): {tenant.name} (ID: {tenant_id})")

    return None


# ============================================================================
# TENANT-GROUP ASSOCIATIONS
# ============================================================================

@router.post("/{tenant_id}/groups", response_model=GroupTenantResponse)
async def associate_group_to_tenant(
    tenant_id: str,
    association_data: GroupTenantCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """
    Associa un gruppo a un tenant

    Il gruppo potrà accedere ai nodi del tenant
    """
    try:
        association = await TenantService.associate_group_to_tenant(
            db=db,
            group_id=association_data.group_id,
            tenant_id=tenant_id,
            added_by=current_user,
            permissions=association_data.permissions
        )

        logger.info(f"🔗 Group {association_data.group_id} associated to tenant {tenant_id}")

        return association

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{tenant_id}/groups", response_model=List[GroupTenantResponse])
async def list_tenant_groups(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lista tutti i gruppi associati a un tenant
    """
    # Verifica accesso al tenant
    can_access = await TenantService.can_user_access_tenant(db, current_user, tenant_id)
    if not can_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Non autorizzato ad accedere a questo tenant"
        )

    groups = await TenantService.get_tenant_groups(db, tenant_id)

    return groups


# ============================================================================
# TENANT-NODE ASSOCIATIONS
# ============================================================================

@router.post("/{tenant_id}/nodes", response_model=TenantNodeResponse)
async def associate_node_to_tenant(
    tenant_id: str,
    association_data: TenantNodeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """
    Associa un nodo edge a un tenant

    Il nodo diventa disponibile per i gruppi del tenant
    """
    try:
        association = await TenantService.associate_node_to_tenant(
            db=db,
            tenant_id=tenant_id,
            node_id=association_data.node_id,
            added_by=current_user,
            node_config=association_data.node_config
        )

        logger.info(f"🔗 Node {association_data.node_id} associated to tenant {tenant_id}")

        return association

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{tenant_id}/nodes", response_model=List[TenantNodeResponse])
async def list_tenant_nodes(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lista tutti i nodi associati a un tenant
    """
    # Verifica accesso al tenant
    can_access = await TenantService.can_user_access_tenant(db, current_user, tenant_id)
    if not can_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Non autorizzato ad accedere a questo tenant"
        )

    nodes = await TenantService.get_tenant_nodes(db, tenant_id)

    return nodes


# ============================================================================
# TENANT STATISTICS
# ============================================================================

@router.get("/{tenant_id}/statistics", response_model=TenantStatistics)
async def get_tenant_statistics(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ottieni statistiche tenant
    """
    # Verifica accesso al tenant
    can_access = await TenantService.can_user_access_tenant(db, current_user, tenant_id)
    if not can_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Non autorizzato ad accedere a questo tenant"
        )

    stats = await TenantService.get_tenant_statistics(db, tenant_id)

    return stats


# ============================================================================
# USER TENANT ACCESS
# ============================================================================

@router.get("/me/accessible", response_model=TenantList)
async def get_my_accessible_tenants(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ottieni tutti i tenant accessibili all'utente corrente
    """
    tenants = await TenantService.get_user_tenants(db, current_user)

    return TenantList(
        tenants=tenants,
        total=len(tenants),
        offset=0,
        limit=len(tenants)
    )
