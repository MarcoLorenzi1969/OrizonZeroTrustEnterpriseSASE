"""
Orizon Zero Trust - Hierarchy Service
Gestisce la gerarchia multi-tenant degli utenti
Gerarchia: SUPERUSER -> SUPER_ADMIN -> ADMIN -> USER
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List, Set, Optional
from app.models.user import User, UserRole


class HierarchyService:
    """Service per gestire la gerarchia degli utenti nel sistema multi-tenant"""
    
    @staticmethod
    def get_role_level(role: UserRole) -> int:
        """
        Ottieni il livello numerico del ruolo nella gerarchia
        Più alto = più potere
        """
        role_levels = {
            UserRole.SUPERUSER: 4,      # Marco - vede tutto
            UserRole.SUPER_ADMIN: 3,    # Distributori
            UserRole.ADMIN: 2,          # Rivenditori
            UserRole.USER: 1,           # Clienti finali
        }
        return role_levels.get(role, 0)
    
    @staticmethod
    def can_manage_role(manager_role: UserRole, target_role: UserRole) -> bool:
        """
        Verifica se un ruolo può gestire (creare/modificare) un altro ruolo
        Es: SUPER_ADMIN può creare ADMIN e USER, ma non SUPERUSER
        """
        manager_level = HierarchyService.get_role_level(manager_role)
        target_level = HierarchyService.get_role_level(target_role)
        return manager_level > target_level
    
    @staticmethod
    async def get_subordinate_users(
        db: AsyncSession,
        user: User,
        include_self: bool = False
    ) -> List[User]:
        """
        Ottieni tutti gli utenti subordinati nella gerarchia
        
        Logica:
        - SUPERUSER: vede TUTTI gli utenti
        - SUPER_ADMIN: vede se stesso + tutti gli ADMIN e USER creati da lui e dai suoi subordinati
        - ADMIN: vede se stesso + tutti gli USER creati da lui
        - USER: vede solo se stesso
        
        Args:
            db: Sessione database
            user: Utente corrente
            include_self: Se includere l'utente stesso nella lista
        
        Returns:
            Lista di utenti subordinati
        """
        subordinates = set()
        
        if include_self:
            subordinates.add(user.id)
        
        # SUPERUSER vede TUTTI
        if user.role == UserRole.SUPERUSER:
            query = select(User)
            if not include_self:
                query = query.where(User.id != user.id)
            result = await db.execute(query)
            return list(result.scalars().all())
        
        # Per gli altri ruoli, usa ricorsione per trovare tutti i subordinati
        await HierarchyService._get_subordinates_recursive(
            db, user.id, subordinates
        )
        
        # Recupera gli oggetti User
        if subordinates:
            query = select(User).where(User.id.in_(subordinates))
            result = await db.execute(query)
            return list(result.scalars().all())
        
        return []
    
    @staticmethod
    async def _get_subordinates_recursive(
        db: AsyncSession,
        user_id: str,
        collected: Set[str]
    ):
        """
        Funzione ricorsiva per trovare tutti gli utenti subordinati
        """
        # Trova tutti gli utenti creati da questo utente
        query = select(User).where(User.created_by_id == user_id)
        result = await db.execute(query)
        direct_subordinates = result.scalars().all()
        
        for subordinate in direct_subordinates:
            if subordinate.id not in collected:
                collected.add(subordinate.id)
                # Ricorsivamente trova i subordinati di questo utente
                await HierarchyService._get_subordinates_recursive(
                    db, subordinate.id, collected
                )
    
    @staticmethod
    async def get_subordinate_user_ids(
        db: AsyncSession,
        user: User,
        include_self: bool = False
    ) -> List[str]:
        """
        Ottieni solo gli ID degli utenti subordinati (più efficiente)
        """
        users = await HierarchyService.get_subordinate_users(db, user, include_self)
        return [u.id for u in users]
    
    @staticmethod
    async def can_access_user(
        db: AsyncSession,
        accessor: User,
        target_user_id: str
    ) -> bool:
        """
        Verifica se un utente può accedere/vedere un altro utente
        
        Args:
            db: Sessione database
            accessor: Utente che vuole accedere
            target_user_id: ID dell'utente target
        
        Returns:
            True se può accedere, False altrimenti
        """
        # Un utente può sempre vedere se stesso
        if accessor.id == target_user_id:
            return True
        
        # SUPERUSER può vedere tutti
        if accessor.role == UserRole.SUPERUSER:
            return True
        
        # Verifica se target_user_id è tra i subordinati
        subordinate_ids = await HierarchyService.get_subordinate_user_ids(
            db, accessor, include_self=False
        )
        return target_user_id in subordinate_ids
    
    @staticmethod
    async def get_hierarchy_tree(
        db: AsyncSession,
        root_user: User
    ) -> dict:
        """
        Ottieni l'albero gerarchico completo partendo da un utente
        Utile per debug e visualizzazione
        
        Returns:
            Dizionario con struttura ad albero della gerarchia
        """
        async def build_tree(user: User) -> dict:
            # Trova utenti creati direttamente da questo utente
            query = select(User).where(User.created_by_id == user.id)
            result = await db.execute(query)
            children = result.scalars().all()
            
            tree = {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value,
                "is_active": user.is_active,
                "children": []
            }
            
            # Ricorsivamente costruisci l'albero per ogni figlio
            for child in children:
                tree["children"].append(await build_tree(child))
            
            return tree
        
        return await build_tree(root_user)
    
    @staticmethod
    async def get_user_path(
        db: AsyncSession,
        user: User
    ) -> List[dict]:
        """
        Ottieni il percorso gerarchico dall'utente root fino all'utente corrente
        Es: [SUPERUSER] -> [SUPER_ADMIN] -> [ADMIN] -> [USER]
        
        Returns:
            Lista di dict con info utenti nel path
        """
        path = []
        current = user
        
        while current:
            path.insert(0, {
                "id": current.id,
                "email": current.email,
                "full_name": current.full_name,
                "role": current.role.value
            })
            
            if current.created_by_id:
                current = await db.get(User, current.created_by_id)
            else:
                break
        
        return path
