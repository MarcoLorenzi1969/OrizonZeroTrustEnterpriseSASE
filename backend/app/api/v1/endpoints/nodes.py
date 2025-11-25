"""
Orizon Zero Trust Connect - Nodes Endpoints
For: Marco @ Syneto/Orizon

Node management with QR code provisioning
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4
import secrets
import httpx

from app.core.database import get_db
from app.core.config import settings
from app.auth.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.node import Node, NodeStatus, ExposedApplication
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
    Create a new node with reverse tunnel configuration

    Requires authentication. Users can only create nodes for themselves.
    Admins can create nodes for any user.

    The agent_token returned should be used in the installation script.
    """
    # Generate unique agent token
    agent_token = f"agt_{secrets.token_urlsafe(32)}"

    # Build application_ports with defaults if not provided
    application_ports = {}
    for app in node_data.exposed_applications:
        app_value = app.value if hasattr(app, 'value') else app

        if node_data.application_ports and app_value in node_data.application_ports:
            # Use provided config
            port_config = node_data.application_ports[app_value]
            application_ports[app_value] = {
                "local": port_config.local,
                "remote": port_config.remote
            }
        else:
            # Use defaults
            temp_node = Node()
            defaults = temp_node.get_default_ports_for_application(ExposedApplication(app_value))
            application_ports[app_value] = defaults

    # Auto-assign remote ports if not specified
    base_remote_port = 10000
    used_ports = set()
    for app_name, ports in application_ports.items():
        if ports.get("remote") is None:
            # Find next available port
            while base_remote_port in used_ports:
                base_remote_port += 1
            ports["remote"] = base_remote_port
            used_ports.add(base_remote_port)
            base_remote_port += 1
        else:
            used_ports.add(ports["remote"])

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
        agent_token=agent_token,
        reverse_tunnel_type=node_data.reverse_tunnel_type.value if hasattr(node_data.reverse_tunnel_type, 'value') else node_data.reverse_tunnel_type,
        exposed_applications=[app.value if hasattr(app, 'value') else app for app in node_data.exposed_applications],
        application_ports=application_ports,
    )

    db.add(node)
    await db.commit()
    await db.refresh(node)

    logger.info(f"📦 Node created: {node.name} (ID: {node.id}, Tunnel: {node.reverse_tunnel_type}) by user {current_user.username}")

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
    if current_user.role != UserRole.SUPERUSER:
        if not accessible_node_ids:
            # User not in any group, return empty list
            return NodeList(nodes=[], total=0)
        query = query.where(Node.id.in_(accessible_node_ids))

    # Apply status filter
    if status_filter:
        query = query.where(Node.status == status_filter)

    # Get total count
    count_query = select(Node)
    if current_user.role != UserRole.SUPERUSER:
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
    if current_user.role != UserRole.SUPERUSER:
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
    if (current_user.role not in [UserRole.SUPERUSER, UserRole.SUPER_ADMIN, UserRole.ADMIN]
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
    if (current_user.role not in [UserRole.SUPERUSER, UserRole.SUPER_ADMIN, UserRole.ADMIN]
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
    if (current_user.role not in [UserRole.SUPERUSER, UserRole.SUPER_ADMIN, UserRole.ADMIN]
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


# === Script Generation Endpoints ===

@router.get("/{node_id}/install-script/{os_type}", response_class=PlainTextResponse)
async def get_install_script(
    node_id: str,
    os_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate installation script for a specific OS

    os_type: linux, macos, or windows
    Returns the script as plain text for download
    """
    # Validate OS type
    if os_type not in ['linux', 'macos', 'windows']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OS type. Must be linux, macos, or windows"
        )

    # Get node
    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()

    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Node not found"
        )

    # Check permissions via groups
    if current_user.role != UserRole.SUPERUSER:
        accessible_node_ids = await GroupService.get_accessible_nodes_for_user(db, current_user)
        if node_id not in accessible_node_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this node"
            )

    # Prepare script generation request
    script_request = {
        "nodeId": node.id,
        "nodeName": node.name,
        "agentToken": node.agent_token,
        "hubHost": settings.HUB_HOST,
        "hubSshPort": settings.HUB_SSH_PORT,
        "tunnelType": node.reverse_tunnel_type,
        "apiBaseUrl": settings.API_BASE_URL,
        "applicationPorts": node.application_ports or {}
    }

    try:
        # Call script-generator microservice
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.SCRIPT_GENERATOR_URL}/api/scripts/generate/{os_type}",
                json=script_request,
                timeout=30.0
            )

            if response.status_code != 200:
                logger.error(f"Script generator error: {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to generate script"
                )

            script_content = response.text

            logger.info(f"📜 Script generated for node {node.name} ({os_type})")

            # Set appropriate filename
            extension = '.ps1' if os_type == 'windows' else '.sh'
            filename = f"orizon-install-{node.name}{extension}"

            return PlainTextResponse(
                content=script_content,
                media_type="text/plain",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"'
                }
            )

    except httpx.RequestError as e:
        logger.error(f"❌ Failed to connect to script generator: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Script generator service unavailable"
        )


@router.get("/{node_id}/install-scripts")
async def get_all_install_scripts(
    node_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate installation scripts for all platforms

    Returns scripts for Linux, macOS, and Windows
    """
    # Get node
    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()

    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Node not found"
        )

    # Check permissions via groups
    if current_user.role != UserRole.SUPERUSER:
        accessible_node_ids = await GroupService.get_accessible_nodes_for_user(db, current_user)
        if node_id not in accessible_node_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this node"
            )

    # Prepare script generation request
    script_request = {
        "nodeId": node.id,
        "nodeName": node.name,
        "agentToken": node.agent_token,
        "hubHost": settings.HUB_HOST,
        "hubSshPort": settings.HUB_SSH_PORT,
        "tunnelType": node.reverse_tunnel_type,
        "apiBaseUrl": settings.API_BASE_URL,
        "applicationPorts": node.application_ports or {}
    }

    try:
        # Call script-generator microservice
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.SCRIPT_GENERATOR_URL}/api/scripts/generate-all",
                json=script_request,
                timeout=30.0
            )

            if response.status_code != 200:
                logger.error(f"Script generator error: {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to generate scripts"
                )

            scripts_data = response.json()

            logger.info(f"📜 All scripts generated for node {node.name}")

            return {
                "nodeId": node.id,
                "nodeName": node.name,
                "scripts": scripts_data.get("scripts", {}),
                "downloadUrls": {
                    "linux": f"/api/v1/nodes/{node_id}/install-script/linux",
                    "macos": f"/api/v1/nodes/{node_id}/install-script/macos",
                    "windows": f"/api/v1/nodes/{node_id}/install-script/windows"
                }
            }

    except httpx.RequestError as e:
        logger.error(f"❌ Failed to connect to script generator: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Script generator service unavailable"
        )
