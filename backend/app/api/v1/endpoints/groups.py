"""
Orizon Zero Trust Connect - Groups Endpoints
For: Marco @ Syneto/Orizon

Group-Based Access Control API
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.auth.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.group import GroupRole
from app.schemas.group import (
    GroupCreate,
    GroupUpdate,
    GroupResponse,
    GroupList,
    AddUserToGroup,
    AddUsersToGroup,
    UpdateUserRoleInGroup,
    GroupMemberResponse,
    GroupMembersList,
    AddNodeToGroup,
    AddNodesToGroup,
    UpdateNodePermissionsInGroup,
    GroupNodeResponse,
    GroupNodesList,
    CheckAccessRequest,
    CheckAccessResponse,
)
from app.services.group_service import GroupService
from loguru import logger

router = APIRouter()


# ==================== GROUP CRUD ====================

@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    group_data: GroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_USER, UserRole.SUPER_ADMIN, UserRole.ADMIN])),
):
    """
    Create a new group

    Requires ADMIN+ role.
    Creator is automatically added as OWNER.
    """
    group = await GroupService.create_group(
        db=db,
        name=group_data.name,
        description=group_data.description,
        settings=group_data.settings or {},
        created_by=current_user
    )

    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        settings=group.settings,
        created_by=group.created_by,
        created_at=group.created_at,
        updated_at=group.updated_at,
        is_active=group.is_active,
        member_count=1,  # Creator
        node_count=0
    )


@router.get("", response_model=GroupList)
async def list_groups(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    include_inactive: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all groups accessible by current user

    - SUPERUSER sees all groups
    - Others see only groups they belong to
    """
    groups = await GroupService.get_groups_by_user(
        db=db,
        user=current_user,
        include_inactive=include_inactive
    )

    # Apply pagination
    total = len(groups)
    groups_page = groups[skip:skip + limit]

    # Build responses with counts
    group_responses = []
    for group in groups_page:
        members = await GroupService.get_group_members(db, group.id)
        nodes = await GroupService.get_group_nodes(db, group.id)

        group_responses.append(GroupResponse(
            id=group.id,
            name=group.name,
            description=group.description,
            settings=group.settings,
            created_by=group.created_by,
            created_at=group.created_at,
            updated_at=group.updated_at,
            is_active=group.is_active,
            member_count=len(members),
            node_count=len(nodes)
        ))

    return GroupList(groups=group_responses, total=total)


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get group by ID"""
    group = await GroupService.get_group_by_id(db, group_id)

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )

    # Check if user has access to this group
    if current_user.role != UserRole.SUPER_USER:
        user_role = await GroupService.get_user_role_in_group(
            db, user_id=current_user.id, group_id=group_id
        )
        if not user_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this group"
            )

    # Get counts
    members = await GroupService.get_group_members(db, group.id)
    nodes = await GroupService.get_group_nodes(db, group.id)

    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        settings=group.settings,
        created_by=group.created_by,
        created_at=group.created_at,
        updated_at=group.updated_at,
        is_active=group.is_active,
        member_count=len(members),
        node_count=len(nodes)
    )


@router.put("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: str,
    group_data: GroupUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update group

    Requires OWNER or ADMIN role in group, or SUPERUSER
    """
    group = await GroupService.update_group(
        db=db,
        group_id=group_id,
        name=group_data.name,
        description=group_data.description,
        settings=group_data.settings,
        current_user=current_user
    )

    # Get counts
    members = await GroupService.get_group_members(db, group.id)
    nodes = await GroupService.get_group_nodes(db, group.id)

    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        settings=group.settings,
        created_by=group.created_by,
        created_at=group.created_at,
        updated_at=group.updated_at,
        is_active=group.is_active,
        member_count=len(members),
        node_count=len(nodes)
    )


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete group (soft delete)

    Only OWNER or SUPERUSER can delete
    """
    await GroupService.delete_group(db, group_id, current_user)
    logger.info(f"🗑️ Group {group_id} deleted by {current_user.email}")


# ==================== GROUP MEMBERS ====================

@router.get("/{group_id}/members", response_model=GroupMembersList)
async def get_group_members(
    group_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all members of a group"""
    # Verify group exists and user has access
    group = await GroupService.get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )

    # Check access
    if current_user.role != UserRole.SUPER_USER:
        user_role = await GroupService.get_user_role_in_group(
            db, user_id=current_user.id, group_id=group_id
        )
        if not user_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

    members = await GroupService.get_group_members(db, group_id)

    member_responses = [
        GroupMemberResponse(
            user_id=m["user_id"],
            email=m["email"],
            username=m["username"],
            full_name=m["full_name"],
            role_in_group=m["role_in_group"],
            permissions=m["permissions"],
            added_at=m["added_at"]
        )
        for m in members
    ]

    return GroupMembersList(members=member_responses, total=len(member_responses))


@router.post("/{group_id}/members", status_code=status.HTTP_201_CREATED)
async def add_user_to_group(
    group_id: str,
    user_data: AddUserToGroup,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_USER, UserRole.SUPER_ADMIN, UserRole.ADMIN])),
):
    """
    Add user to group

    Requires OWNER or ADMIN in group, or SUPERUSER
    """
    # Check permissions
    if current_user.role != UserRole.SUPER_USER:
        user_role = await GroupService.get_user_role_in_group(
            db, user_id=current_user.id, group_id=group_id
        )
        if user_role not in [GroupRole.OWNER, GroupRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )

    user_group = await GroupService.add_user_to_group(
        db=db,
        group_id=group_id,
        user_id=user_data.user_id,
        role_in_group=user_data.role_in_group,
        added_by=current_user,
        permissions=user_data.permissions
    )

    logger.info(f"👥 User {user_data.user_id} added to group {group_id} by {current_user.email}")
    return {"message": "User added to group successfully"}


@router.post("/{group_id}/members/bulk", status_code=status.HTTP_201_CREATED)
async def add_users_to_group(
    group_id: str,
    users_data: AddUsersToGroup,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_USER, UserRole.SUPER_ADMIN, UserRole.ADMIN])),
):
    """Add multiple users to group"""
    # Check permissions
    if current_user.role != UserRole.SUPER_USER:
        user_role = await GroupService.get_user_role_in_group(
            db, user_id=current_user.id, group_id=group_id
        )
        if user_role not in [GroupRole.OWNER, GroupRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )

    added_count = 0
    for user_id in users_data.user_ids:
        try:
            await GroupService.add_user_to_group(
                db=db,
                group_id=group_id,
                user_id=user_id,
                role_in_group=users_data.role_in_group,
                added_by=current_user,
                permissions=users_data.permissions
            )
            added_count += 1
        except HTTPException:
            logger.warning(f"User {user_id} already in group or not found")
            continue

    logger.info(f"👥 {added_count} users added to group {group_id}")
    return {"message": f"{added_count} users added successfully"}


@router.delete("/{group_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user_from_group(
    group_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove user from group"""
    await GroupService.remove_user_from_group(db, group_id, user_id, current_user)
    logger.info(f"👥 User {user_id} removed from group {group_id}")


@router.put("/{group_id}/members/{user_id}", status_code=status.HTTP_200_OK)
async def update_user_role(
    group_id: str,
    user_id: str,
    role_data: UpdateUserRoleInGroup,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update user role in group"""
    user_group = await GroupService.update_user_role_in_group(
        db=db,
        group_id=group_id,
        user_id=user_id,
        new_role=role_data.role_in_group,
        current_user=current_user
    )

    logger.info(f"👥 User {user_id} role updated to {role_data.role_in_group} in group {group_id}")
    return {"message": "User role updated successfully"}


# ==================== GROUP NODES ====================

@router.get("/{group_id}/nodes", response_model=GroupNodesList)
async def get_group_nodes(
    group_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all nodes in a group"""
    # Verify access
    if current_user.role != UserRole.SUPER_USER:
        user_role = await GroupService.get_user_role_in_group(
            db, user_id=current_user.id, group_id=group_id
        )
        if not user_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

    nodes = await GroupService.get_group_nodes(db, group_id)

    node_responses = [
        GroupNodeResponse(
            node_id=n["node_id"],
            name=n["name"],
            hostname=n["hostname"],
            status=n["status"],
            node_type=n["node_type"],
            permissions=n["permissions"],
            added_at=n["added_at"]
        )
        for n in nodes
    ]

    return GroupNodesList(nodes=node_responses, total=len(node_responses))


@router.post("/{group_id}/nodes", status_code=status.HTTP_201_CREATED)
async def add_node_to_group(
    group_id: str,
    node_data: AddNodeToGroup,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_USER, UserRole.SUPER_ADMIN, UserRole.ADMIN])),
):
    """Add node to group"""
    # Check permissions
    if current_user.role != UserRole.SUPER_USER:
        user_role = await GroupService.get_user_role_in_group(
            db, user_id=current_user.id, group_id=group_id
        )
        if user_role not in [GroupRole.OWNER, GroupRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )

    node_group = await GroupService.add_node_to_group(
        db=db,
        group_id=group_id,
        node_id=node_data.node_id,
        permissions=node_data.permissions,
        added_by=current_user
    )

    logger.info(f"🖥️ Node {node_data.node_id} added to group {group_id}")
    return {"message": "Node added to group successfully"}


@router.post("/{group_id}/nodes/bulk", status_code=status.HTTP_201_CREATED)
async def add_nodes_to_group(
    group_id: str,
    nodes_data: AddNodesToGroup,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPER_USER, UserRole.SUPER_ADMIN, UserRole.ADMIN])),
):
    """Add multiple nodes to group"""
    # Check permissions
    if current_user.role != UserRole.SUPER_USER:
        user_role = await GroupService.get_user_role_in_group(
            db, user_id=current_user.id, group_id=group_id
        )
        if user_role not in [GroupRole.OWNER, GroupRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )

    added_count = 0
    for node_id in nodes_data.node_ids:
        try:
            await GroupService.add_node_to_group(
                db=db,
                group_id=group_id,
                node_id=node_id,
                permissions=nodes_data.permissions,
                added_by=current_user
            )
            added_count += 1
        except HTTPException:
            logger.warning(f"Node {node_id} already in group or not found")
            continue

    logger.info(f"🖥️ {added_count} nodes added to group {group_id}")
    return {"message": f"{added_count} nodes added successfully"}


@router.delete("/{group_id}/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_node_from_group(
    group_id: str,
    node_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove node from group"""
    await GroupService.remove_node_from_group(db, group_id, node_id, current_user)
    logger.info(f"🖥️ Node {node_id} removed from group {group_id}")


@router.put("/{group_id}/nodes/{node_id}", status_code=status.HTTP_200_OK)
async def update_node_permissions(
    group_id: str,
    node_id: str,
    perm_data: UpdateNodePermissionsInGroup,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update node permissions in group"""
    node_group = await GroupService.update_node_permissions_in_group(
        db=db,
        group_id=group_id,
        node_id=node_id,
        permissions=perm_data.permissions,
        current_user=current_user
    )

    logger.info(f"🖥️ Node {node_id} permissions updated in group {group_id}")
    return {"message": "Node permissions updated successfully"}


# ==================== ACCESS CONTROL ====================

@router.post("/check-access", response_model=CheckAccessResponse)
async def check_node_access(
    access_request: CheckAccessRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check if current user has access to a node"""
    has_access = await GroupService.check_user_node_access(
        db=db,
        user=current_user,
        node_id=access_request.node_id,
        permission_type=access_request.permission_type
    )

    return CheckAccessResponse(
        has_access=has_access,
        reason="Access granted" if has_access else "No permission via groups"
    )
