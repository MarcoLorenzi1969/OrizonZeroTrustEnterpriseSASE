"""
Orizon Zero Trust - Permission Service
Gestione permessi utenti per accesso nodi e servizi
"""
from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, delete
from datetime import datetime, timedelta
import json

from app.models.user import User
from app.models.node import Node
from app.models.group import UserGroup
from app.models.user_permissions import (
    user_node_permissions,
    GroupNodePermission,
    AccessLog,
    TunnelSession,
    PermissionLevel,
    ServiceType
)
from loguru import logger


class PermissionService:
    """Servizio per gestione permessi granulari"""

    @staticmethod
    async def grant_user_permission(
        db: AsyncSession,
        user_id: str,
        node_id: str,
        granted_by_id: str,
        permission_level: PermissionLevel,
        services: Dict[str, bool],
        expires_at: Optional[datetime] = None,
        ip_whitelist: Optional[List[str]] = None,
        notes: Optional[str] = None
    ) -> Dict:
        """Assegna permessi a un utente per un nodo"""

        # Verifica che utente e nodo esistano
        user = await db.get(User, user_id)
        node = await db.get(Node, node_id)

        if not user or not node:
            raise ValueError("User or Node not found")

        # Crea permesso
        permission_data = {
            "user_id": user_id,
            "node_id": node_id,
            "permission_level": permission_level,
            "can_ssh": services.get("ssh", False),
            "can_rdp": services.get("rdp", False),
            "can_vnc": services.get("vnc", False),
            "can_http": services.get("http", False),
            "can_https": services.get("https", False),
            "allowed_services": json.dumps(services.get("custom", [])) if services.get("custom") else None,
            "ip_whitelist": json.dumps(ip_whitelist) if ip_whitelist else None,
            "granted_by": granted_by_id,
            "granted_at": datetime.utcnow(),
            "expires_at": expires_at,
            "is_active": True,
            "notes": notes
        }

        # Verifica se esiste già un permesso
        result = await db.execute(
            select(user_node_permissions).where(
                and_(
                    user_node_permissions.c.user_id == user_id,
                    user_node_permissions.c.node_id == node_id
                )
            )
        )
        existing = result.first()

        if existing:
            # Aggiorna permesso esistente
            await db.execute(
                user_node_permissions.update().where(
                    user_node_permissions.c.id == existing.id
                ).values(**permission_data)
            )
        else:
            # Inserisci nuovo permesso
            await db.execute(user_node_permissions.insert().values(**permission_data))

        await db.commit()

        logger.info(f"✅ Permission granted: user={user.email}, node={node.name}, level={permission_level}")

        return {
            "user_id": user_id,
            "node_id": node_id,
            "permission_level": permission_level,
            "services": services
        }

    @staticmethod
    async def revoke_user_permission(
        db: AsyncSession,
        user_id: str,
        node_id: str
    ) -> bool:
        """Revoca permessi utente per un nodo"""

        result = await db.execute(
            delete(user_node_permissions).where(
                and_(
                    user_node_permissions.c.user_id == user_id,
                    user_node_permissions.c.node_id == node_id
                )
            )
        )
        await db.commit()

        logger.info(f"✅ Permission revoked: user_id={user_id}, node_id={node_id}")
        return result.rowcount > 0

    @staticmethod
    async def check_user_access(
        db: AsyncSession,
        user_id: str,
        node_id: str,
        service_type: ServiceType,
        source_ip: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """Verifica se un utente può accedere a un servizio su un nodo"""

        # Controlla permessi diretti utente
        result = await db.execute(
            select(user_node_permissions).where(
                and_(
                    user_node_permissions.c.user_id == user_id,
                    user_node_permissions.c.node_id == node_id,
                    user_node_permissions.c.is_active == True
                )
            )
        )
        permission = result.first()

        if not permission:
            # Controlla permessi tramite gruppi
            has_group_access, reason = await PermissionService._check_group_access(
                db, user_id, node_id, service_type
            )
            if not has_group_access:
                return False, "No permission found for this node"
            permission = has_group_access

        # Verifica scadenza
        if permission.expires_at and permission.expires_at < datetime.utcnow():
            return False, "Permission expired"

        # Verifica IP whitelist
        if permission.ip_whitelist and source_ip:
            allowed_ips = json.loads(permission.ip_whitelist)
            if source_ip not in allowed_ips:
                return False, f"IP {source_ip} not in whitelist"

        # Verifica permesso per servizio specifico
        service_map = {
            ServiceType.SSH: permission.can_ssh,
            ServiceType.RDP: permission.can_rdp,
            ServiceType.VNC: permission.can_vnc,
            ServiceType.HTTP: permission.can_http,
            ServiceType.HTTPS: permission.can_https
        }

        if service_type in service_map:
            if not service_map[service_type]:
                return False, f"Service {service_type} not allowed"

        # Verifica livello permesso
        if permission.permission_level == PermissionLevel.NO_ACCESS:
            return False, "Access explicitly denied"

        if permission.permission_level == PermissionLevel.VIEW_ONLY:
            return False, "View-only permission, cannot connect"

        return True, None

    @staticmethod
    async def _check_group_access(
        db: AsyncSession,
        user_id: str,
        node_id: str,
        service_type: ServiceType
    ) -> tuple[Optional[object], Optional[str]]:
        """Verifica accesso tramite appartenenza a gruppi"""

        # Ottieni gruppi dell'utente
        result = await db.execute(
            select(UserGroup).where(
                UserGroup.user_id == user_id
            )
        )
        memberships = result.scalars().all()

        for membership in memberships:
            # Controlla permessi del gruppo
            group_perm_result = await db.execute(
                select(GroupNodePermission).where(
                    and_(
                        GroupNodePermission.group_id == membership.group_id,
                        GroupNodePermission.node_id == node_id,
                        GroupNodePermission.is_active == True
                    )
                )
            )
            group_perm = group_perm_result.scalar_one_or_none()

            if group_perm:
                return group_perm, None

        return None, "No group permission found"

    @staticmethod
    async def get_user_permissions(
        db: AsyncSession,
        user_id: str
    ) -> List[Dict]:
        """Ottieni tutti i permessi di un utente"""

        result = await db.execute(
            select(user_node_permissions).where(
                and_(
                    user_node_permissions.c.user_id == user_id,
                    user_node_permissions.c.is_active == True
                )
            )
        )
        permissions = result.all()

        perm_list = []
        for perm in permissions:
            # Ottieni info nodo
            node = await db.get(Node, perm.node_id)

            perm_list.append({
                "node_id": perm.node_id,
                "node_name": node.name if node else "Unknown",
                "permission_level": perm.permission_level,
                "services": {
                    "ssh": perm.can_ssh,
                    "rdp": perm.can_rdp,
                    "vnc": perm.can_vnc,
                    "http": perm.can_http,
                    "https": perm.can_https
                },
                "granted_at": perm.granted_at.isoformat(),
                "expires_at": perm.expires_at.isoformat() if perm.expires_at else None,
                "notes": perm.notes
            })

        return perm_list

    @staticmethod
    async def log_access(
        db: AsyncSession,
        user_id: str,
        node_id: str,
        service_type: ServiceType,
        action: str,
        source_ip: str,
        success: bool = True,
        error_message: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Registra un tentativo di accesso"""

        log = AccessLog(
            user_id=user_id,
            node_id=node_id,
            service_type=service_type,
            action=action,
            source_ip=source_ip,
            success=success,
            error_message=error_message,
            session_id=session_id,
            metadata=json.dumps(metadata) if metadata else None,
            timestamp=datetime.utcnow()
        )

        db.add(log)
        await db.commit()

        logger.info(f"📊 Access logged: user_id={user_id}, node_id={node_id}, service={service_type}, success={success}")

    @staticmethod
    async def create_tunnel_session(
        db: AsyncSession,
        user_id: str,
        node_id: str,
        service_type: ServiceType,
        tunnel_id: str,
        local_port: int,
        remote_port: int,
        source_ip: str,
        metadata: Optional[Dict] = None
    ) -> TunnelSession:
        """Crea una sessione tunnel attiva"""

        session = TunnelSession(
            user_id=user_id,
            node_id=node_id,
            service_type=service_type,
            tunnel_id=tunnel_id,
            local_port=str(local_port),
            remote_port=str(remote_port),
            source_ip=source_ip,
            status="active",
            started_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            connection_metadata=json.dumps(metadata) if metadata else None
        )

        db.add(session)
        await db.commit()
        await db.refresh(session)

        logger.info(f"🔌 Tunnel session created: {tunnel_id} (user={user_id}, node={node_id}, service={service_type})")

        return session

    @staticmethod
    async def get_active_tunnels(
        db: AsyncSession,
        user_id: Optional[str] = None,
        node_id: Optional[str] = None
    ) -> List[TunnelSession]:
        """Ottieni tunnel attivi"""

        query = select(TunnelSession).where(TunnelSession.status == "active")

        if user_id:
            query = query.where(TunnelSession.user_id == user_id)
        if node_id:
            query = query.where(TunnelSession.node_id == node_id)

        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def close_tunnel_session(
        db: AsyncSession,
        tunnel_id: str
    ) -> bool:
        """Chiudi una sessione tunnel"""

        result = await db.execute(
            select(TunnelSession).where(TunnelSession.tunnel_id == tunnel_id)
        )
        session = result.scalar_one_or_none()

        if session:
            session.status = "disconnected"
            session.ended_at = datetime.utcnow()
            await db.commit()

            logger.info(f"🔌 Tunnel session closed: {tunnel_id}")
            return True

        return False

    @staticmethod
    async def grant_group_permission(
        db: AsyncSession,
        group_id: str,
        node_id: str,
        granted_by_id: str,
        permission_level: PermissionLevel,
        services: Dict[str, bool]
    ) -> GroupNodePermission:
        """Assegna permessi a un gruppo per un nodo"""

        permission = GroupNodePermission(
            group_id=group_id,
            node_id=node_id,
            permission_level=permission_level,
            can_ssh=services.get("ssh", False),
            can_rdp=services.get("rdp", False),
            can_vnc=services.get("vnc", False),
            can_http=services.get("http", False),
            can_https=services.get("https", False),
            granted_by=granted_by_id,
            is_active=True
        )

        db.add(permission)
        await db.commit()
        await db.refresh(permission)

        logger.info(f"👥 Group permission granted: group_id={group_id}, node_id={node_id}")
        return permission
