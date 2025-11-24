"""
Orizon Zero Trust - Node Visibility Service
Gestisce la visibilità dei nodi in base alla gerarchia multi-tenant
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List, Optional
from app.models.user import User, UserRole
from app.models.node import Node
from app.services.hierarchy_service import HierarchyService


class NodeVisibilityService:
    """Service per gestire la visibilità dei nodi basata sulla gerarchia utenti"""

    @staticmethod
    async def get_visible_nodes(
        db: AsyncSession,
        user: User,
        include_inactive: bool = False
    ) -> List[Node]:
        """
        Ottieni tutti i nodi visibili all'utente in base alla gerarchia

        Logica:
        - SUPERUSER: vede TUTTI i nodi nel sistema
        - SUPER_ADMIN: vede i propri nodi + nodi di tutti gli ADMIN e USER sotto di lui
        - ADMIN: vede i propri nodi + nodi di tutti gli USER che ha creato
        - USER: vede solo i propri nodi

        Args:
            db: Sessione database
            user: Utente corrente
            include_inactive: Se includere nodi non attivi

        Returns:
            Lista di nodi visibili
        """
        # SUPERUSER vede TUTTI i nodi
        if user.role == UserRole.SUPERUSER:
            query = select(Node)
            if not include_inactive:
                query = query.where(Node.is_active == True)
            result = await db.execute(query)
            return list(result.scalars().all())

        # Per altri ruoli, ottieni IDs di tutti gli utenti subordinati
        subordinate_ids = await HierarchyService.get_subordinate_user_ids(
            db, user, include_self=True  # Includi l'utente stesso
        )

        # Filtra nodi posseduti da utenti visibili
        query = select(Node).where(Node.owner_id.in_(subordinate_ids))

        if not include_inactive:
            query = query.where(Node.is_active == True)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_visible_node_ids(
        db: AsyncSession,
        user: User,
        include_inactive: bool = False
    ) -> List[str]:
        """
        Ottieni solo gli ID dei nodi visibili (più efficiente)
        """
        nodes = await NodeVisibilityService.get_visible_nodes(db, user, include_inactive)
        return [node.id for node in nodes]

    @staticmethod
    async def can_access_node(
        db: AsyncSession,
        user: User,
        node_id: str
    ) -> bool:
        """
        Verifica se un utente può accedere/vedere un nodo specifico

        Args:
            db: Sessione database
            user: Utente che vuole accedere
            node_id: ID del nodo target

        Returns:
            True se può accedere, False altrimenti
        """
        # SUPERUSER può vedere tutti i nodi
        if user.role == UserRole.SUPERUSER:
            return True

        # Verifica se il nodo è tra quelli visibili
        visible_node_ids = await NodeVisibilityService.get_visible_node_ids(
            db, user, include_inactive=True  # Permetti accesso anche a nodi inattivi
        )
        return node_id in visible_node_ids

    @staticmethod
    async def get_nodes_by_owner(
        db: AsyncSession,
        user: User,
        owner_id: str,
        include_inactive: bool = False
    ) -> List[Node]:
        """
        Ottieni i nodi di un proprietario specifico, se l'utente ha accesso

        Args:
            db: Sessione database
            user: Utente corrente
            owner_id: ID del proprietario dei nodi
            include_inactive: Se includere nodi non attivi

        Returns:
            Lista di nodi se l'utente ha accesso, altrimenti lista vuota
        """
        # Verifica se l'utente può vedere il proprietario
        can_access = await HierarchyService.can_access_user(db, user, owner_id)

        if not can_access:
            return []

        # Ottieni i nodi del proprietario
        query = select(Node).where(Node.owner_id == owner_id)

        if not include_inactive:
            query = query.where(Node.is_active == True)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_nodes_statistics(
        db: AsyncSession,
        user: User
    ) -> dict:
        """
        Ottieni statistiche sui nodi visibili all'utente
        Utile per dashboard e debug

        Returns:
            Dict con statistiche:
            - total_nodes: Totale nodi visibili
            - active_nodes: Nodi attivi
            - inactive_nodes: Nodi inattivi
            - nodes_by_owner: Dict con conteggio nodi per proprietario
            - nodes_by_type: Dict con conteggio per tipo servizio
        """
        all_nodes = await NodeVisibilityService.get_visible_nodes(
            db, user, include_inactive=True
        )

        active_nodes = [n for n in all_nodes if n.is_active]
        inactive_nodes = [n for n in all_nodes if not n.is_active]

        # Raggruppa per proprietario
        nodes_by_owner = {}
        for node in all_nodes:
            if node.owner_id not in nodes_by_owner:
                nodes_by_owner[node.owner_id] = 0
            nodes_by_owner[node.owner_id] += 1

        # Raggruppa per tipo servizio
        nodes_by_type = {}
        for node in all_nodes:
            service_type = node.service_type.value if node.service_type else "unknown"
            if service_type not in nodes_by_type:
                nodes_by_type[service_type] = 0
            nodes_by_type[service_type] += 1

        return {
            "total_nodes": len(all_nodes),
            "active_nodes": len(active_nodes),
            "inactive_nodes": len(inactive_nodes),
            "nodes_by_owner": nodes_by_owner,
            "nodes_by_type": nodes_by_type
        }

    @staticmethod
    async def get_node_with_owner_info(
        db: AsyncSession,
        user: User,
        node_id: str
    ) -> Optional[dict]:
        """
        Ottieni informazioni complete su un nodo inclusi i dati del proprietario
        Solo se l'utente ha accesso

        Returns:
            Dict con info nodo + proprietario, o None se non accessibile
        """
        # Verifica accesso
        can_access = await NodeVisibilityService.can_access_node(db, user, node_id)

        if not can_access:
            return None

        # Ottieni il nodo
        node = await db.get(Node, node_id)

        if not node:
            return None

        # Ottieni info proprietario
        owner = await db.get(User, node.owner_id)

        # Ottieni il percorso gerarchico del proprietario
        owner_path = await HierarchyService.get_user_path(db, owner) if owner else []

        return {
            "node": {
                "id": node.id,
                "name": node.name,
                "service_type": node.service_type.value if node.service_type else None,
                "host": node.host,
                "port": node.port,
                "is_active": node.is_active,
                "created_at": node.created_at.isoformat() if node.created_at else None,
                "updated_at": node.updated_at.isoformat() if node.updated_at else None,
            },
            "owner": {
                "id": owner.id,
                "email": owner.email,
                "full_name": owner.full_name,
                "role": owner.role.value,
            } if owner else None,
            "owner_hierarchy_path": owner_path
        }
