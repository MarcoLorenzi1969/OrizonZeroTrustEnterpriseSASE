"""
Orizon Zero Trust Connect - Group Service
For: Marco @ Syneto/Orizon
Business logic for group-based access control
"""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from app.models.group import Group, UserGroup, NodeGroup, GroupRole
from app.models.user import User, UserRole
from app.models.node import Node
from loguru import logger


class GroupService:
    """Service for group operations"""

    @staticmethod
    async def create_group(
        db: AsyncSession,
        name: str,
        description: Optional[str],
        settings: Dict[str, Any],
        created_by: User
    ) -> Group:
        """
        Create new group

        Args:
            db: Database session
            name: Group name (unique)
            description: Optional description
            settings: Group settings dict
            created_by: User creating the group

        Returns:
            Created group

        Raises:
            HTTPException: If name already exists
        """
        try:
            # Check if name already exists
            result = await db.execute(
                select(Group).where(Group.name == name)
            )
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Group '{name}' already exists"
                )

            # Create group
            group = Group(
                id=str(uuid.uuid4()),
                name=name,
                description=description,
                settings=settings or {},
                created_by=created_by.id,
                created_at=datetime.utcnow(),
                is_active=True
            )

            db.add(group)
            await db.commit()
            await db.refresh(group)

            # Auto-add creator as OWNER
            await GroupService.add_user_to_group(
                db=db,
                group_id=group.id,
                user_id=created_by.id,
                role_in_group=GroupRole.OWNER,
                added_by=created_by
            )

            logger.info(f"Group created: {group.name} by {created_by.email}")
            return group

        except IntegrityError as e:
            await db.rollback()
            logger.error(f"Error creating group: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error creating group"
            )

    @staticmethod
    async def get_group_by_id(
        db: AsyncSession,
        group_id: str,
        load_associations: bool = False
    ) -> Optional[Group]:
        """Get group by ID"""
        query = select(Group).where(Group.id == group_id, Group.is_active == True)

        if load_associations:
            query = query.options(
                selectinload(Group.user_associations),
                selectinload(Group.node_associations)
            )

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_groups_by_user(
        db: AsyncSession,
        user: User,
        include_inactive: bool = False
    ) -> List[Group]:
        """
        Get all groups accessible by user

        Args:
            db: Database session
            user: Current user
            include_inactive: Include inactive groups

        Returns:
            List of groups
        """
        # SUPERUSER sees all groups
        if user.role == UserRole.SUPERUSER:
            query = select(Group)
            if not include_inactive:
                query = query.where(Group.is_active == True)
            result = await db.execute(query)
            return list(result.scalars().all())

        # Other users see only their groups
        query = (
            select(Group)
            .join(UserGroup, UserGroup.group_id == Group.id)
            .where(UserGroup.user_id == user.id)
        )

        if not include_inactive:
            query = query.where(Group.is_active == True)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def update_group(
        db: AsyncSession,
        group_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
        current_user: Optional[User] = None
    ) -> Group:
        """Update group details"""
        group = await GroupService.get_group_by_id(db, group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Group not found"
            )

        # Check permissions (OWNER or ADMIN in group, or SUPERUSER)
        if current_user and current_user.role != UserRole.SUPERUSER:
            user_role = await GroupService.get_user_role_in_group(
                db, user_id=current_user.id, group_id=group_id
            )
            if user_role not in [GroupRole.OWNER, GroupRole.ADMIN]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions to update group"
                )

        if name:
            group.name = name
        if description is not None:
            group.description = description
        if settings is not None:
            group.settings = settings

        group.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(group)

        logger.info(f"Group updated: {group.name}")
        return group

    @staticmethod
    async def delete_group(
        db: AsyncSession,
        group_id: str,
        current_user: User
    ) -> bool:
        """
        Soft delete group (set is_active=False)
        Only OWNER or SUPERUSER can delete
        """
        group = await GroupService.get_group_by_id(db, group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Group not found"
            )

        # Check permissions
        if current_user.role != UserRole.SUPERUSER:
            user_role = await GroupService.get_user_role_in_group(
                db, user_id=current_user.id, group_id=group_id
            )
            if user_role != GroupRole.OWNER:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only group OWNER can delete the group"
                )

        # Soft delete
        group.is_active = False
        group.updated_at = datetime.utcnow()

        await db.commit()
        logger.info(f"Group deleted: {group.name} by {current_user.email}")
        return True

    # ==================== USER-GROUP OPERATIONS ====================

    @staticmethod
    async def add_user_to_group(
        db: AsyncSession,
        group_id: str,
        user_id: str,
        role_in_group: GroupRole,
        added_by: User,
        permissions: Optional[Dict[str, Any]] = None
    ) -> UserGroup:
        """Add user to group"""
        # Check if already member
        result = await db.execute(
            select(UserGroup).where(
                and_(
                    UserGroup.user_id == user_id,
                    UserGroup.group_id == group_id
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already in group"
            )

        # Create association
        user_group = UserGroup(
            id=str(uuid.uuid4()),
            user_id=user_id,
            group_id=group_id,
            role_in_group=role_in_group,
            permissions=permissions or {},
            added_by=added_by.id,
            added_at=datetime.utcnow()
        )

        db.add(user_group)
        await db.commit()
        await db.refresh(user_group)

        logger.info(f"User {user_id} added to group {group_id} as {role_in_group}")
        return user_group

    @staticmethod
    async def remove_user_from_group(
        db: AsyncSession,
        group_id: str,
        user_id: str,
        current_user: User
    ) -> bool:
        """Remove user from group"""
        # Check permissions
        if current_user.role != UserRole.SUPERUSER:
            user_role = await GroupService.get_user_role_in_group(
                db, user_id=current_user.id, group_id=group_id
            )
            if user_role not in [GroupRole.OWNER, GroupRole.ADMIN]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )

        # Delete association
        await db.execute(
            delete(UserGroup).where(
                and_(
                    UserGroup.user_id == user_id,
                    UserGroup.group_id == group_id
                )
            )
        )
        await db.commit()

        logger.info(f"User {user_id} removed from group {group_id}")
        return True

    @staticmethod
    async def get_group_members(
        db: AsyncSession,
        group_id: str
    ) -> List[Dict[str, Any]]:
        """Get all members of a group with their roles"""
        result = await db.execute(
            select(UserGroup, User)
            .join(User, User.id == UserGroup.user_id)
            .where(UserGroup.group_id == group_id)
            .options(selectinload(UserGroup.user))
        )

        members = []
        for user_group, user in result.all():
            members.append({
                "user_id": user.id,
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name,
                "role_in_group": user_group.role_in_group,
                "permissions": user_group.permissions,
                "added_at": user_group.added_at
            })

        return members

    @staticmethod
    async def get_user_role_in_group(
        db: AsyncSession,
        user_id: str,
        group_id: str
    ) -> Optional[GroupRole]:
        """Get user's role in a specific group"""
        result = await db.execute(
            select(UserGroup.role_in_group).where(
                and_(
                    UserGroup.user_id == user_id,
                    UserGroup.group_id == group_id
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_user_role_in_group(
        db: AsyncSession,
        group_id: str,
        user_id: str,
        new_role: GroupRole,
        current_user: User
    ) -> UserGroup:
        """Update user's role in group"""
        # Check permissions (OWNER or SUPERUSER)
        if current_user.role != UserRole.SUPERUSER:
            user_role = await GroupService.get_user_role_in_group(
                db, user_id=current_user.id, group_id=group_id
            )
            if user_role != GroupRole.OWNER:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only OWNER can change roles"
                )

        result = await db.execute(
            update(UserGroup)
            .where(
                and_(
                    UserGroup.user_id == user_id,
                    UserGroup.group_id == group_id
                )
            )
            .values(role_in_group=new_role)
            .returning(UserGroup)
        )

        await db.commit()
        user_group = result.scalar_one_or_none()

        if not user_group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not in group"
            )

        logger.info(f"User {user_id} role updated to {new_role} in group {group_id}")
        return user_group

    # ==================== NODE-GROUP OPERATIONS ====================

    @staticmethod
    async def add_node_to_group(
        db: AsyncSession,
        group_id: str,
        node_id: str,
        permissions: Dict[str, bool],
        added_by: User
    ) -> NodeGroup:
        """Add node to group"""
        # Check if already in group
        result = await db.execute(
            select(NodeGroup).where(
                and_(
                    NodeGroup.node_id == node_id,
                    NodeGroup.group_id == group_id
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Node already in group"
            )

        # Create association
        node_group = NodeGroup(
            id=str(uuid.uuid4()),
            node_id=node_id,
            group_id=group_id,
            permissions=permissions,
            added_by=added_by.id,
            added_at=datetime.utcnow()
        )

        db.add(node_group)
        await db.commit()
        await db.refresh(node_group)

        logger.info(f"Node {node_id} added to group {group_id}")
        return node_group

    @staticmethod
    async def remove_node_from_group(
        db: AsyncSession,
        group_id: str,
        node_id: str,
        current_user: User
    ) -> bool:
        """Remove node from group"""
        # Check permissions
        if current_user.role != UserRole.SUPERUSER:
            user_role = await GroupService.get_user_role_in_group(
                db, user_id=current_user.id, group_id=group_id
            )
            if user_role not in [GroupRole.OWNER, GroupRole.ADMIN]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )

        await db.execute(
            delete(NodeGroup).where(
                and_(
                    NodeGroup.node_id == node_id,
                    NodeGroup.group_id == group_id
                )
            )
        )
        await db.commit()

        logger.info(f"Node {node_id} removed from group {group_id}")
        return True

    @staticmethod
    async def get_group_nodes(
        db: AsyncSession,
        group_id: str
    ) -> List[Dict[str, Any]]:
        """Get all nodes in a group with permissions"""
        result = await db.execute(
            select(NodeGroup, Node)
            .join(Node, Node.id == NodeGroup.node_id)
            .where(NodeGroup.group_id == group_id)
        )

        nodes = []
        for node_group, node in result.all():
            nodes.append({
                "node_id": node.id,
                "name": node.name,
                "hostname": node.hostname,
                "status": node.status,
                "node_type": node.node_type,
                "permissions": node_group.permissions,
                "added_at": node_group.added_at
            })

        return nodes

    @staticmethod
    async def update_node_permissions_in_group(
        db: AsyncSession,
        group_id: str,
        node_id: str,
        permissions: Dict[str, bool],
        current_user: User
    ) -> NodeGroup:
        """Update node permissions in group"""
        # Check permissions
        if current_user.role != UserRole.SUPERUSER:
            user_role = await GroupService.get_user_role_in_group(
                db, user_id=current_user.id, group_id=group_id
            )
            if user_role not in [GroupRole.OWNER, GroupRole.ADMIN]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )

        result = await db.execute(
            update(NodeGroup)
            .where(
                and_(
                    NodeGroup.node_id == node_id,
                    NodeGroup.group_id == group_id
                )
            )
            .values(permissions=permissions)
            .returning(NodeGroup)
        )

        await db.commit()
        node_group = result.scalar_one_or_none()

        if not node_group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Node not in group"
            )

        logger.info(f"Node {node_id} permissions updated in group {group_id}")
        return node_group

    # ==================== ACCESS CONTROL CHECKS ====================

    @staticmethod
    async def check_user_node_access(
        db: AsyncSession,
        user: User,
        node_id: str,
        permission_type: str = "ssh"
    ) -> bool:
        """
        Check if user has access to node via groups

        Args:
            db: Database session
            user: Current user
            node_id: Target node ID
            permission_type: Permission to check (ssh, rdp, vnc)

        Returns:
            True if user has access, False otherwise
        """
        # SUPERUSER bypasses all checks
        if user.role == UserRole.SUPERUSER:
            return True

        # Get user's groups
        result = await db.execute(
            select(UserGroup.group_id).where(UserGroup.user_id == user.id)
        )
        user_group_ids = [row[0] for row in result.all()]

        if not user_group_ids:
            return False  # User not in any group

        # Check if node is in any of user's groups with required permission
        result = await db.execute(
            select(NodeGroup.permissions)
            .where(
                and_(
                    NodeGroup.node_id == node_id,
                    NodeGroup.group_id.in_(user_group_ids)
                )
            )
        )

        for (permissions,) in result.all():
            if permissions.get(permission_type, False):
                return True  # Found at least one group with permission

        return False

    @staticmethod
    async def get_accessible_nodes_for_user(
        db: AsyncSession,
        user: User
    ) -> List[str]:
        """
        Get list of node IDs accessible by user via groups

        Returns:
            List of node IDs
        """
        # SUPERUSER sees all nodes
        if user.role == UserRole.SUPERUSER:
            result = await db.execute(select(Node.id))
            return [row[0] for row in result.all()]

        # Get user's groups
        result = await db.execute(
            select(UserGroup.group_id).where(UserGroup.user_id == user.id)
        )
        user_group_ids = [row[0] for row in result.all()]

        if not user_group_ids:
            return []

        # Get nodes in those groups
        result = await db.execute(
            select(NodeGroup.node_id)
            .where(NodeGroup.group_id.in_(user_group_ids))
            .distinct()
        )

        return [row[0] for row in result.all()]
