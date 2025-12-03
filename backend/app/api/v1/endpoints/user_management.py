"""
Orizon Zero Trust - User Management Endpoints
API per gestione utenti, permessi e accessi
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid
from pydantic import BaseModel, EmailStr
from datetime import datetime

from app.core.database import get_db
from app.auth.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.user_permissions import PermissionLevel, ServiceType
from app.services.permission_service import PermissionService
from app.services.user_service import UserService
from app.services.hierarchy_service import HierarchyService
from app.auth.security import get_password_hash


router = APIRouter()


# Schemas

class UserCreateRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: UserRole = UserRole.USER
    is_active: bool = True


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class PasswordChangeRequest(BaseModel):
    new_password: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None


class PermissionGrantRequest(BaseModel):
    user_id: str
    node_id: str
    permission_level: PermissionLevel
    services: dict  # {"ssh": true, "rdp": false, "vnc": true, ...}
    expires_at: Optional[datetime] = None
    ip_whitelist: Optional[List[str]] = None
    notes: Optional[str] = None


class PermissionResponse(BaseModel):
    node_id: str
    node_name: str
    permission_level: str
    services: dict
    granted_at: str
    expires_at: Optional[str]


class UserGroupCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None


class GroupMemberRequest(BaseModel):
    user_id: str


class GroupPermissionRequest(BaseModel):
    node_id: str
    permission_level: PermissionLevel
    services: dict


class TunnelRequestSchema(BaseModel):
    node_id: str
    service_type: ServiceType
    remote_port: Optional[int] = None


class AccessLogResponse(BaseModel):
    id: str
    user_email: str
    node_name: str
    service_type: str
    action: str
    source_ip: str
    success: bool
    timestamp: datetime


# Endpoints - User Management

@router.post("/users", response_model=UserResponse, dependencies=[Depends(require_role([UserRole.SUPERUSER, UserRole.SUPER_ADMIN, UserRole.ADMIN]))])
async def create_user(
    user_data: UserCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crea un nuovo utente seguendo la gerarchia:
    - SUPERUSER: può creare SUPER_ADMIN, ADMIN, USER
    - SUPER_ADMIN: può creare ADMIN, USER
    - ADMIN: può creare solo USER
    """

    # Verifica che l'utente possa creare il ruolo richiesto
    if not HierarchyService.can_manage_role(current_user.role, user_data.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot create user with role {user_data.role.value}. Your role ({current_user.role.value}) can only create lower-level roles."
        )

    # Verifica se email esiste già
    existing = await UserService.get_user_by_email(db, user_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Crea utente con created_by_id per tracciare la gerarchia
    username = user_data.email.split("@")[0]
    new_user = User(
        id=str(uuid.uuid4()),
        email=user_data.email,
        username=username,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
        role=user_data.role,
        is_active=user_data.is_active,
        created_by_id=current_user.id,  # Traccia chi ha creato l'utente
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        full_name=new_user.full_name,
        role=new_user.role,
        is_active=new_user.is_active,
        created_at=new_user.created_at,
        last_login=new_user.last_login
    )


@router.get("/users", response_model=List[UserResponse], dependencies=[Depends(require_role([UserRole.SUPERUSER, UserRole.SUPER_ADMIN, UserRole.ADMIN]))])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lista utenti in base alla gerarchia:
    - SUPERUSER: vede tutti gli utenti
    - SUPER_ADMIN: vede se stesso + ADMIN e USER che ha creato (e loro subordinati)
    - ADMIN: vede se stesso + USER che ha creato
    """

    # Usa HierarchyService per ottenere solo gli utenti visibili
    users = await HierarchyService.get_subordinate_users(db, current_user, include_self=True)

    # Applica paginazione
    paginated_users = users[skip:skip + limit]

    return [
        UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login=user.last_login
        )
        for user in paginated_users
    ]


@router.get("/users/{user_id}", response_model=UserResponse, dependencies=[Depends(require_role([UserRole.SUPERUSER, UserRole.SUPER_ADMIN, UserRole.ADMIN]))])
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Ottieni dettagli utente (solo se nella propria gerarchia)"""

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verifica che l'utente sia accessibile nella gerarchia
    can_access = await HierarchyService.can_access_user(db, current_user, user_id)
    if not can_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this user"
        )

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login=user.last_login
    )


@router.put("/users/{user_id}", response_model=UserResponse, dependencies=[Depends(require_role([UserRole.SUPERUSER, UserRole.SUPER_ADMIN, UserRole.ADMIN]))])
async def update_user(
    user_id: str,
    user_data: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Aggiorna utente (solo se nella propria gerarchia)"""

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verifica che l'utente sia accessibile nella gerarchia
    can_access = await HierarchyService.can_access_user(db, current_user, user_id)
    if not can_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user"
        )

    # Se si vuole cambiare il ruolo, verifica che sia permesso
    if user_data.role is not None:
        if not HierarchyService.can_manage_role(current_user.role, user_data.role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cannot assign role {user_data.role.value}. Your role can only manage lower-level roles."
            )

    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    if user_data.role is not None:
        user.role = user_data.role
    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    await db.commit()
    await db.refresh(user)

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login=user.last_login
    )


@router.delete("/users/{user_id}", dependencies=[Depends(require_role([UserRole.SUPERUSER, UserRole.SUPER_ADMIN, UserRole.ADMIN]))])
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Elimina utente (solo se nella propria gerarchia)"""

    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verifica che l'utente sia accessibile nella gerarchia
    can_access = await HierarchyService.can_access_user(db, current_user, user_id)
    if not can_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this user"
        )

    # Non permettere di eliminare utenti di pari o superiore livello
    if not HierarchyService.can_manage_role(current_user.role, user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot delete user with role {user.role.value}. Your role can only delete lower-level users."
        )

    await db.delete(user)
    await db.commit()

    return {"message": "User deleted successfully"}


@router.put("/users/{user_id}/password", dependencies=[Depends(require_role([UserRole.SUPERUSER, UserRole.SUPER_ADMIN, UserRole.ADMIN]))])
async def change_user_password(
    user_id: str,
    password_data: PasswordChangeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cambia password di un utente (solo se nella propria gerarchia)"""

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verifica che l'utente sia accessibile nella gerarchia
    can_access = await HierarchyService.can_access_user(db, current_user, user_id)
    if not can_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to change this user's password"
        )

    # Non permettere di cambiare password di utenti di pari o superiore livello
    if user_id != current_user.id and not HierarchyService.can_manage_role(current_user.role, user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot change password for user with role {user.role.value}"
        )

    # Validate password length
    if len(password_data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters"
        )

    user.hashed_password = get_password_hash(password_data.new_password)
    await db.commit()

    return {"message": "Password changed successfully"}


# Endpoints - Permissions

@router.post("/permissions/grant", dependencies=[Depends(require_role([UserRole.SUPERUSER, UserRole.SUPER_ADMIN, UserRole.ADMIN]))])
async def grant_permission(
    perm_data: PermissionGrantRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Assegna permessi a un utente per un nodo"""

    try:
        result = await PermissionService.grant_user_permission(
            db=db,
            user_id=perm_data.user_id,
            node_id=perm_data.node_id,
            granted_by_id=current_user.id,
            permission_level=perm_data.permission_level,
            services=perm_data.services,
            expires_at=perm_data.expires_at,
            ip_whitelist=perm_data.ip_whitelist,
            notes=perm_data.notes
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/permissions/revoke")
async def revoke_permission(
    user_id: str,
    node_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Revoca permessi utente per un nodo"""

    # Solo admin o lo stesso utente
    if current_user.role not in [UserRole.SUPERUSER, UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        if current_user.id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

    success = await PermissionService.revoke_user_permission(db, user_id, node_id)

    if not success:
        raise HTTPException(status_code=404, detail="Permission not found")

    return {"message": "Permission revoked successfully"}


@router.get("/permissions/user/{user_id}", response_model=List[PermissionResponse])
async def get_user_permissions(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Ottieni permessi di un utente"""

    # Utente può vedere solo i propri permessi, admin può vedere tutti
    if current_user.role not in [UserRole.SUPERUSER, UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        if current_user.id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

    permissions = await PermissionService.get_user_permissions(db, user_id)

    return [PermissionResponse(**perm) for perm in permissions]


@router.get("/permissions/my", response_model=List[PermissionResponse])
async def get_my_permissions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Ottieni i miei permessi"""

    permissions = await PermissionService.get_user_permissions(db, current_user.id)
    return [PermissionResponse(**perm) for perm in permissions]


# Endpoints - User Groups

@router.post("/groups", dependencies=[Depends(require_role([UserRole.SUPERUSER, UserRole.SUPER_ADMIN]))])
async def create_group(
    group_data: UserGroupCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Crea un nuovo gruppo utenti"""

    group = await PermissionService.create_user_group(
        db=db,
        name=group_data.name,
        description=group_data.description,
        created_by_id=current_user.id
    )

    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "created_at": group.created_at.isoformat()
    }


@router.post("/groups/{group_id}/members", dependencies=[Depends(require_role([UserRole.SUPERUSER, UserRole.SUPER_ADMIN]))])
async def add_group_member(
    group_id: str,
    member_data: GroupMemberRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Aggiungi utente a un gruppo"""

    membership = await PermissionService.add_user_to_group(
        db=db,
        user_id=member_data.user_id,
        group_id=group_id,
        added_by_id=current_user.id
    )

    return {"message": "User added to group successfully"}


@router.post("/groups/{group_id}/permissions", dependencies=[Depends(require_role([UserRole.SUPERUSER, UserRole.SUPER_ADMIN]))])
async def grant_group_permission(
    group_id: str,
    perm_data: GroupPermissionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Assegna permessi a un gruppo per un nodo"""

    permission = await PermissionService.grant_group_permission(
        db=db,
        group_id=group_id,
        node_id=perm_data.node_id,
        granted_by_id=current_user.id,
        permission_level=perm_data.permission_level,
        services=perm_data.services
    )

    return {"message": "Group permission granted successfully"}


# Endpoints - Access Logs

@router.get("/access-logs", response_model=List[AccessLogResponse], dependencies=[Depends(require_role([UserRole.SUPERUSER, UserRole.SUPER_ADMIN, UserRole.ADMIN]))])
async def get_access_logs(
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[str] = None,
    node_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Ottieni log degli accessi"""

    from app.models.user_permissions import AccessLog
    from sqlalchemy import select, desc

    query = select(AccessLog).order_by(desc(AccessLog.timestamp)).offset(skip).limit(limit)

    if user_id:
        query = query.where(AccessLog.user_id == user_id)
    if node_id:
        query = query.where(AccessLog.node_id == node_id)

    result = await db.execute(query)
    logs = result.scalars().all()

    response = []
    for log in logs:
        user = await db.get(User, log.user_id) if log.user_id else None
        from app.models.node import Node
        node = await db.get(Node, log.node_id) if log.node_id else None

        response.append(AccessLogResponse(
            id=log.id,
            user_email=user.email if user else "Unknown",
            node_name=node.name if node else "Unknown",
            service_type=log.service_type,
            action=log.action,
            source_ip=log.source_ip,
            success=log.success,
            timestamp=log.timestamp
        ))

    return response


# Endpoints - Tunnel Sessions

@router.get("/tunnels/active")
async def get_active_tunnels(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Ottieni tunnel attivi dell'utente"""

    tunnels = await PermissionService.get_active_tunnels(db, user_id=current_user.id)

    return [
        {
            "tunnel_id": t.tunnel_id,
            "node_id": t.node_id,
            "service_type": t.service_type,
            "local_port": t.local_port,
            "remote_port": t.remote_port,
            "status": t.status,
            "started_at": t.started_at.isoformat(),
            "last_activity": t.last_activity.isoformat()
        }
        for t in tunnels
    ]


@router.post("/tunnels/close/{tunnel_id}")
async def close_tunnel(
    tunnel_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Chiudi un tunnel attivo"""

    success = await PermissionService.close_tunnel_session(db, tunnel_id)

    if not success:
        raise HTTPException(status_code=404, detail="Tunnel not found")

    return {"message": "Tunnel closed successfully"}
