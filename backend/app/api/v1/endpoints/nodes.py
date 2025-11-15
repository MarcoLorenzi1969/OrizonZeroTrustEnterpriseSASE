"""
Orizon Zero Trust Connect - Nodes Endpoints
For: Marco @ Syneto/Orizon

Node management with QR code provisioning
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4

from app.core.database import get_db
from app.core.config import settings
from app.auth.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.node import Node, NodeStatus
from app.schemas.node import (
    NodeCreate,
    NodeUpdate,
    NodeResponse,
    NodeList,
    ProvisionRequest,
    ProvisionData,
    ServiceConfig,
)
from app.services.node_provision_service import NodeProvisioningService
from app.services.group_service import GroupService
from loguru import logger

router = APIRouter()


# === CRUD Operations ===

@router.post("", response_model=NodeResponse, status_code=status.HTTP_201_CREATED)
async def create_node(
    node_data: NodeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new node

    Requires authentication. Users can only create nodes for themselves.
    Admins can create nodes for any user.
    """
    # Create node
    node = Node(
        id=str(uuid4()),
        name=node_data.name,
        hostname=node_data.hostname,
        node_type=node_data.node_type,
        public_ip=node_data.public_ip,
        private_ip=node_data.private_ip,
        location=node_data.location,
        tags=node_data.tags,
        status=NodeStatus.OFFLINE,
        owner_id=current_user.id,
    )

    db.add(node)
    await db.commit()
    await db.refresh(node)

    logger.info(f"📦 Node created: {node.name} (ID: {node.id}) by user {current_user.username}")

    return node


@router.get("", response_model=NodeList)
async def list_nodes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status_filter: NodeStatus = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all nodes accessible by current user

    - SUPERUSER sees all nodes
    - Others see nodes in their groups (group-based access control)
    """
    # Get accessible node IDs via groups
    accessible_node_ids = await GroupService.get_accessible_nodes_for_user(db, current_user)

    # Build query
    query = select(Node)

    # Filter by accessible nodes (group-based)
    if current_user.role != UserRole.SUPER_USER:
        if not accessible_node_ids:
            # User not in any group, return empty list
            return NodeList(nodes=[], total=0)
        query = query.where(Node.id.in_(accessible_node_ids))

    # Apply status filter
    if status_filter:
        query = query.where(Node.status == status_filter)

    # Get total count
    count_query = select(Node)
    if current_user.role != UserRole.SUPER_USER:
        count_query = count_query.where(Node.id.in_(accessible_node_ids))
    result = await db.execute(count_query)
    total = len(result.scalars().all())

    # Apply pagination
    query = query.offset(skip).limit(limit)

    # Execute query
    result = await db.execute(query)
    nodes = result.scalars().all()

    return NodeList(nodes=nodes, total=total)


@router.get("/{node_id}", response_model=NodeResponse)
async def get_node(
    node_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get node by ID

    Users can access nodes in their groups (group-based access control)
    """
    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()

    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Node not found"
        )

    # Check permissions via groups
    if current_user.role != UserRole.SUPER_USER:
        accessible_node_ids = await GroupService.get_accessible_nodes_for_user(db, current_user)
        if node_id not in accessible_node_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this node (no group access)"
            )

    return node


@router.patch("/{node_id}", response_model=NodeResponse)
async def update_node(
    node_id: str,
    node_data: NodeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update node

    Users can only update their own nodes.
    Admins can update any node.
    """
    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()

    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Node not found"
        )

    # Check permissions
    if (current_user.role not in [UserRole.SUPER_USER, UserRole.SUPER_ADMIN, UserRole.ADMIN]
        and node.owner_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this node"
        )

    # Update fields
    update_data = node_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(node, field, value)

    await db.commit()
    await db.refresh(node)

    logger.info(f"📝 Node updated: {node.name} (ID: {node.id})")

    return node


@router.delete("/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_node(
    node_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete node

    Users can only delete their own nodes.
    Admins can delete any node.
    """
    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()

    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Node not found"
        )

    # Check permissions
    if (current_user.role not in [UserRole.SUPER_USER, UserRole.SUPER_ADMIN, UserRole.ADMIN]
        and node.owner_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this node"
        )

    await db.delete(node)
    await db.commit()

    logger.info(f"🗑️  Node deleted: {node.name} (ID: {node.id})")

    return None


# === Provisioning Endpoints ===

@router.post("/{node_id}/provision", response_model=ProvisionData)
async def generate_provision_data(
    node_id: str,
    services: List[ServiceConfig],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate provisioning data for a node

    Returns:
    - Provision token (JWT with 24h expiration)
    - QR code (base64 PNG data URL)
    - Provision URL
    - Download URLs for Linux/macOS/Windows scripts

    The QR code can be scanned with a mobile device to access the provision page.
    """
    # Check if node exists
    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()

    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Node not found"
        )

    # Check permissions
    if (current_user.role not in [UserRole.SUPER_USER, UserRole.SUPER_ADMIN, UserRole.ADMIN]
        and node.owner_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to provision this node"
        )

    # Initialize provisioning service
    provision_service = NodeProvisioningService(
        api_base_url=settings.API_BASE_URL,
        hub_host=settings.HUB_HOST,
        hub_ssh_port=settings.HUB_SSH_PORT,
    )

    # Convert services to dict format
    services_data = [svc.model_dump() for svc in services]

    # Generate provision data
    try:
        provision_data = provision_service.generate_provision_data(
            node_id=node_id,
            node_name=node.name,
            services=services_data,
        )

        logger.info(f"🔐 Provision data generated for node: {node.name} (ID: {node_id})")

        return ProvisionData(
            node_id=provision_data["node_id"],
            provision_token=provision_data["provision_token"],
            provision_url=provision_data["provision_url"],
            qr_code_data_url=provision_data["qr_code_data_url"],
            download_urls=provision_data["download_urls"],
            services=services,
            expires_at=provision_data["expires_at"],
        )

    except Exception as e:
        logger.error(f"❌ Failed to generate provision data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate provision data: {str(e)}"
        )
