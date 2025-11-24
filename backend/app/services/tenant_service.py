"""
Orizon Zero Trust - Tenant Service
Gestione completa dei tenant e delle associazioni
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import List, Optional, Dict, Any
from app.models.tenant import Tenant, GroupTenant, TenantNode
from app.models.group import Group, UserGroup
from app.models.node import Node
from app.models.user import User, UserRole
from app.services.hierarchy_service import HierarchyService
import uuid
import re


class TenantService:
    """Service per gestione tenant multi-tenant"""

    @staticmethod
    def generate_slug(name: str) -> str:
        """Genera slug da nome tenant"""
        slug = name.lower()
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        slug = slug.strip('-')
        return slug

    @staticmethod
    async def create_tenant(
        db: AsyncSession,
        name: str,
        display_name: str,
        created_by: User,
        description: Optional[str] = None,
        company_info: Optional[Dict] = None,
        settings: Optional[Dict] = None,
        quota: Optional[Dict] = None
    ) -> Tenant:
        """
        Crea nuovo tenant

        Args:
            db: Sessione database
            name: Nome univoco tenant
            display_name: Nome visualizzato
            created_by: Utente che crea il tenant
            description: Descrizione
            company_info: Info azienda
            settings: Configurazione
            quota: Quote e limiti

        Returns:
            Tenant creato
        """
        # Genera slug
        slug = TenantService.generate_slug(name)

        # Verifica unicità slug
        existing = await db.execute(
            select(Tenant).where(Tenant.slug == slug)
        )
        if existing.scalar_one_or_none():
            # Aggiungi suffisso numerico
            counter = 1
            while True:
                new_slug = f"{slug}-{counter}"
                existing = await db.execute(
                    select(Tenant).where(Tenant.slug == new_slug)
                )
                if not existing.scalar_one_or_none():
                    slug = new_slug
                    break
                counter += 1

        # Crea tenant
        tenant = Tenant(
            id=str(uuid.uuid4()),
            name=name,
            display_name=display_name,
            slug=slug,
            description=description,
            company_info=company_info or {},
            settings=settings or {},
            quota=quota or {},
            created_by_id=created_by.id
        )

        db.add(tenant)
        await db.commit()
        await db.refresh(tenant)

        return tenant

    @staticmethod
    async def get_tenant_by_id(
        db: AsyncSession,
        tenant_id: str
    ) -> Optional[Tenant]:
        """Ottieni tenant per ID"""
        result = await db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_tenant_by_slug(
        db: AsyncSession,
        slug: str
    ) -> Optional[Tenant]:
        """Ottieni tenant per slug"""
        result = await db.execute(
            select(Tenant).where(Tenant.slug == slug)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all_tenants(
        db: AsyncSession,
        user: User,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False
    ) -> List[Tenant]:
        """
        Ottieni tutti i tenant visibili all'utente

        Logica visibilità:
        - SUPERUSER: vede TUTTI i tenant
        - SUPER_ADMIN/ADMIN: vede tenant creati da lui e subordinati
        - USER: vede solo tenant accessibili tramite suoi gruppi
        """
        query = select(Tenant)

        if not include_inactive:
            query = query.where(Tenant.is_active == True)

        # SUPERUSER vede tutto
        if user.role == UserRole.SUPERUSER:
            query = query.offset(skip).limit(limit)
            result = await db.execute(query)
            return list(result.scalars().all())

        # SUPER_ADMIN/ADMIN vedono tenant creati da loro e subordinati
        if user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
            subordinate_ids = await HierarchyService.get_subordinate_user_ids(
                db, user, include_self=True
            )
            query = query.where(Tenant.created_by_id.in_(subordinate_ids))
            query = query.offset(skip).limit(limit)
            result = await db.execute(query)
            return list(result.scalars().all())

        # USER vede solo tenant accessibili tramite gruppi
        accessible_tenant_ids = await TenantService.get_user_accessible_tenant_ids(db, user)
        if not accessible_tenant_ids:
            return []

        query = query.where(Tenant.id.in_(accessible_tenant_ids))
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_user_accessible_tenant_ids(
        db: AsyncSession,
        user: User
    ) -> List[str]:
        """
        Ottieni ID di tutti i tenant accessibili all'utente tramite gruppi
        """
        # Ottieni gruppi dell'utente
        user_groups_query = select(UserGroup.group_id).where(
            UserGroup.user_id == user.id
        )
        result = await db.execute(user_groups_query)
        group_ids = [row[0] for row in result.all()]

        if not group_ids:
            return []

        # Ottieni tenant accessibili da questi gruppi
        tenant_query = select(GroupTenant.tenant_id).where(
            and_(
                GroupTenant.group_id.in_(group_ids),
                GroupTenant.is_active == True
            )
        )
        result = await db.execute(tenant_query)
        return [row[0] for row in result.all()]

    @staticmethod
    async def associate_group_to_tenant(
        db: AsyncSession,
        group_id: str,
        tenant_id: str,
        added_by: User,
        permissions: Optional[Dict] = None
    ) -> GroupTenant:
        """
        Associa un gruppo a un tenant

        Il gruppo potrà accedere ai nodi edge di questo tenant
        """
        # Verifica esistenza gruppo e tenant
        group = await db.get(Group, group_id)
        tenant = await db.get(Tenant, tenant_id)

        if not group or not tenant:
            raise ValueError("Gruppo o Tenant non trovato")

        # Verifica se associazione esiste già
        existing = await db.execute(
            select(GroupTenant).where(
                and_(
                    GroupTenant.group_id == group_id,
                    GroupTenant.tenant_id == tenant_id
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Associazione Gruppo-Tenant già esistente")

        # Crea associazione
        association = GroupTenant(
            id=str(uuid.uuid4()),
            group_id=group_id,
            tenant_id=tenant_id,
            permissions=permissions or {},
            added_by_id=added_by.id
        )

        db.add(association)
        await db.commit()
        await db.refresh(association)

        return association

    @staticmethod
    async def associate_node_to_tenant(
        db: AsyncSession,
        tenant_id: str,
        node_id: str,
        added_by: User,
        node_config: Optional[Dict] = None
    ) -> TenantNode:
        """
        Associa un nodo edge a un tenant

        Il nodo diventa disponibile per tutti i gruppi che hanno accesso al tenant
        """
        # Verifica esistenza tenant e nodo
        tenant = await db.get(Tenant, tenant_id)
        node = await db.get(Node, node_id)

        if not tenant or not node:
            raise ValueError("Tenant o Nodo non trovato")

        # Verifica se associazione esiste già
        existing = await db.execute(
            select(TenantNode).where(
                and_(
                    TenantNode.tenant_id == tenant_id,
                    TenantNode.node_id == node_id
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Associazione Tenant-Nodo già esistente")

        # Crea associazione
        association = TenantNode(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            node_id=node_id,
            node_config=node_config or {},
            added_by_id=added_by.id
        )

        db.add(association)
        await db.commit()
        await db.refresh(association)

        return association

    @staticmethod
    async def get_tenant_nodes(
        db: AsyncSession,
        tenant_id: str,
        include_inactive: bool = False
    ) -> List[TenantNode]:
        """Ottieni tutte le associazioni nodo-tenant"""
        query = select(TenantNode).where(
            TenantNode.tenant_id == tenant_id
        )

        if not include_inactive:
            query = query.where(TenantNode.is_active == True)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_tenant_groups(
        db: AsyncSession,
        tenant_id: str,
        include_inactive: bool = False
    ) -> List[GroupTenant]:
        """Ottieni tutte le associazioni gruppo-tenant"""
        query = select(GroupTenant).where(
            GroupTenant.tenant_id == tenant_id
        )

        if not include_inactive:
            query = query.where(GroupTenant.is_active == True)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_user_tenants(
        db: AsyncSession,
        user: User
    ) -> List[Tenant]:
        """
        Ottieni tutti i tenant accessibili dall'utente tramite i suoi gruppi
        """
        tenant_ids = await TenantService.get_user_accessible_tenant_ids(db, user)
        if not tenant_ids:
            return []

        result = await db.execute(
            select(Tenant).where(
                and_(
                    Tenant.id.in_(tenant_ids),
                    Tenant.is_active == True
                )
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def can_user_access_tenant(
        db: AsyncSession,
        user: User,
        tenant_id: str
    ) -> bool:
        """
        Verifica se un utente può accedere a un tenant

        Returns:
            True se può accedere, False altrimenti
        """
        # SUPERUSER può accedere a tutto
        if user.role == UserRole.SUPERUSER:
            return True

        # Verifica se utente ha creato il tenant o è creato da un subordinato
        tenant = await db.get(Tenant, tenant_id)
        if not tenant:
            return False

        if user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
            subordinate_ids = await HierarchyService.get_subordinate_user_ids(
                db, user, include_self=True
            )
            if tenant.created_by_id in subordinate_ids:
                return True

        # Altrimenti verifica accesso tramite gruppi
        accessible_tenant_ids = await TenantService.get_user_accessible_tenant_ids(db, user)
        return tenant_id in accessible_tenant_ids

    @staticmethod
    async def get_tenant_statistics(
        db: AsyncSession,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Ottieni statistiche tenant
        """
        tenant = await db.get(Tenant, tenant_id)
        if not tenant:
            return {}

        # Conta nodi
        nodes_query = select(func.count(TenantNode.id)).where(
            and_(
                TenantNode.tenant_id == tenant_id,
                TenantNode.is_active == True
            )
        )
        total_nodes = await db.scalar(nodes_query) or 0

        # Conta nodi attivi
        active_nodes_query = select(func.count(Node.id)).join(TenantNode).where(
            and_(
                TenantNode.tenant_id == tenant_id,
                TenantNode.is_active == True,
                Node.status == 'online'
            )
        )
        active_nodes = await db.scalar(active_nodes_query) or 0

        # Conta gruppi
        groups_query = select(func.count(GroupTenant.id)).where(
            and_(
                GroupTenant.tenant_id == tenant_id,
                GroupTenant.is_active == True
            )
        )
        total_groups = await db.scalar(groups_query) or 0

        # Conta utenti (tramite gruppi)
        users_query = select(func.count(func.distinct(UserGroup.user_id))).join(
            GroupTenant, UserGroup.group_id == GroupTenant.group_id
        ).where(
            GroupTenant.tenant_id == tenant_id
        )
        total_users = await db.scalar(users_query) or 0

        return {
            "tenant_id": tenant_id,
            "tenant_name": tenant.name,
            "total_nodes": total_nodes,
            "active_nodes": active_nodes,
            "total_groups": total_groups,
            "total_users": total_users,
            "quota": tenant.quota
        }
