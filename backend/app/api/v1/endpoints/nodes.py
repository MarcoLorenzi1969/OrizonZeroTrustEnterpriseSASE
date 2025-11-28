"""
Orizon Zero Trust Connect - Nodes Endpoints
For: Marco @ Syneto/Orizon

Node management with QR code provisioning
"""

from typing import List
from datetime import datetime
import asyncio
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
    HeartbeatRequest,
    HeartbeatResponse,
    NodeMetricsUpdate,
    NodeMetricsResponse,
    ServiceTunnelConfig,
)
from app.services.node_provision_service import NodeProvisioningService
from app.services.group_service import GroupService
from loguru import logger
import redis.asyncio as redis
from datetime import timedelta

router = APIRouter()

# Redis client for proxy tokens (in-memory temporary tokens)
_redis_client = None

async def get_redis_client():
    """Get or create Redis client for proxy tokens."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


# === CRUD Operations ===

@router.post("/", response_model=NodeResponse, status_code=status.HTTP_201_CREATED)
@router.post("", response_model=NodeResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
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

    # Auto-assign service tunnel port (for heartbeat/metrics)
    result = await db.execute(
        select(Node.service_tunnel_port)
        .where(Node.service_tunnel_port.isnot(None))
        .order_by(Node.service_tunnel_port.desc())
    )
    max_service_port = result.scalar()
    service_tunnel_port = (max_service_port or 8999) + 1

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
        service_tunnel_port=service_tunnel_port,
    )

    db.add(node)
    await db.commit()
    await db.refresh(node)

    logger.info(f"📦 Node created: {node.name} (ID: {node.id}, Tunnel: {node.reverse_tunnel_type}) by user {current_user.username}")

    return node


@router.get("/", response_model=NodeList)
@router.get("", response_model=NodeList, include_in_schema=False)
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

    try:
        # Delete related records first (foreign key constraints)
        from sqlalchemy import text
        await db.execute(text("DELETE FROM tenant_nodes WHERE node_id = :node_id"), {"node_id": node_id})
        await db.execute(text("DELETE FROM node_groups WHERE node_id = :node_id"), {"node_id": node_id})
        await db.execute(text("DELETE FROM user_node_permissions WHERE node_id = :node_id"), {"node_id": node_id})
        await db.execute(text("DELETE FROM group_node_permissions WHERE node_id = :node_id"), {"node_id": node_id})

        await db.delete(node)
        await db.commit()

        logger.info(f"🗑️  Node deleted: {node.name} (ID: {node.id})")
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to delete node {node_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete node: {str(e)}"
        )

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


# === Agent Communication Endpoints ===

@router.post("/heartbeat", response_model=HeartbeatResponse)
async def node_heartbeat(
    heartbeat: HeartbeatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Receive heartbeat from node agent.

    This endpoint is called by the agent through the service tunnel
    to report that the node is alive and optionally update system info.

    No user authentication required - uses agent_token for auth.
    """
    # Find node by agent token
    result = await db.execute(
        select(Node).where(Node.agent_token == heartbeat.agent_token)
    )
    node = result.scalar_one_or_none()

    if not node:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid agent token"
        )

    # Update node status and info
    node.status = NodeStatus.ONLINE
    node.last_heartbeat = heartbeat.timestamp or datetime.utcnow()

    if heartbeat.agent_version:
        node.agent_version = heartbeat.agent_version
    if heartbeat.os_version:
        node.os_version = heartbeat.os_version
    if heartbeat.kernel_version:
        node.kernel_version = heartbeat.kernel_version

    await db.commit()

    logger.debug(f"💓 Heartbeat from node {node.name} (ID: {node.id})")

    return HeartbeatResponse(
        status="ok",
        server_time=datetime.utcnow(),
        next_heartbeat_seconds=30,
        commands=[]  # Future: send commands to agent
    )


@router.post("/metrics", response_model=NodeMetricsResponse)
async def update_node_metrics(
    metrics: NodeMetricsUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Receive metrics update from node agent.

    This endpoint is called by the agent to report system metrics
    (CPU, memory, disk usage, etc.)

    No user authentication required - uses agent_token for auth.
    """
    # Find node by agent token
    result = await db.execute(
        select(Node).where(Node.agent_token == metrics.agent_token)
    )
    node = result.scalar_one_or_none()

    if not node:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid agent token"
        )

    # Update metrics
    node.cpu_usage = metrics.cpu_usage
    node.memory_usage = metrics.memory_usage
    node.disk_usage = metrics.disk_usage

    if metrics.cpu_cores:
        node.cpu_cores = metrics.cpu_cores
    if metrics.memory_mb:
        node.memory_mb = metrics.memory_mb
    if metrics.disk_gb:
        node.disk_gb = metrics.disk_gb

    # Also update last heartbeat since metrics implies alive
    node.last_heartbeat = metrics.timestamp or datetime.utcnow()
    node.status = NodeStatus.ONLINE

    await db.commit()

    logger.debug(f"📊 Metrics from node {node.name}: CPU={metrics.cpu_usage}%, MEM={metrics.memory_usage}%, DISK={metrics.disk_usage}%")

    return NodeMetricsResponse(
        status="ok",
        received_at=datetime.utcnow()
    )


@router.get("/{node_id}/service-tunnel-config", response_model=ServiceTunnelConfig)
async def get_service_tunnel_config(
    node_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the service tunnel configuration for a node.

    Returns the hub connection details and port for the service tunnel
    that handles heartbeat and metrics communication.
    """
    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()

    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Node not found"
        )

    # Check permissions
    if current_user.role != UserRole.SUPERUSER:
        accessible_node_ids = await GroupService.get_accessible_nodes_for_user(db, current_user)
        if node_id not in accessible_node_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this node"
            )

    # Assign service tunnel port if not set
    if not node.service_tunnel_port:
        # Find next available port starting from 9000
        result = await db.execute(
            select(Node.service_tunnel_port)
            .where(Node.service_tunnel_port.isnot(None))
            .order_by(Node.service_tunnel_port.desc())
        )
        max_port = result.scalar()
        node.service_tunnel_port = (max_port or 8999) + 1
        await db.commit()
        await db.refresh(node)

    return ServiceTunnelConfig(
        hub_host=settings.HUB_HOST,
        hub_ssh_port=settings.HUB_SSH_PORT,
        service_port=node.service_tunnel_port,
        heartbeat_interval=30,
        metrics_interval=60
    )


@router.post("/check-offline")
async def check_nodes_offline(
    db: AsyncSession = Depends(get_db),
):
    """
    Background task endpoint to mark nodes as offline if no heartbeat received.

    Called periodically by a scheduler or cron job.
    Marks nodes as OFFLINE if last_heartbeat > 90 seconds ago.
    """
    from datetime import timedelta

    threshold = datetime.utcnow() - timedelta(seconds=90)

    result = await db.execute(
        select(Node).where(
            Node.status == NodeStatus.ONLINE,
            Node.last_heartbeat < threshold
        )
    )
    stale_nodes = result.scalars().all()

    count = 0
    for node in stale_nodes:
        node.status = NodeStatus.OFFLINE
        count += 1
        logger.warning(f"⚠️ Node {node.name} marked OFFLINE (no heartbeat since {node.last_heartbeat})")

    if count > 0:
        await db.commit()

    return {"marked_offline": count}


@router.post("/{node_id}/https-proxy-token")
async def generate_https_proxy_token(
    node_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate a secure one-time token for HTTPS proxy access.

    The token is:
    - Valid for 60 seconds only
    - Single-use (deleted after first use)
    - Stored in Redis, not exposed in URLs or logs
    - Tied to specific node and user

    Returns a short opaque token to use with /https-proxy endpoint.
    """
    # Verify node exists and user has access
    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()

    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")

    if node.status != NodeStatus.ONLINE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Node is {node.status.value}"
        )

    # Check permissions
    if current_user.role != UserRole.SUPERUSER:
        accessible_node_ids = await GroupService.get_accessible_nodes_for_user(db, current_user)
        if node_id not in accessible_node_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    # Generate short random token (not JWT - opaque and short)
    proxy_token = secrets.token_urlsafe(32)

    # Store in Redis with 60 second expiry
    redis_client = await get_redis_client()
    token_data = f"{current_user.id}:{node_id}"
    await redis_client.setex(f"proxy_token:{proxy_token}", 60, token_data)

    logger.info(f"🔐 Generated HTTPS proxy token for user={current_user.email}, node={node.name}")

    return {"proxy_token": proxy_token, "expires_in": 60}


@router.get("/{node_id}/https-proxy")
async def https_proxy(
    node_id: str,
    t: str = Query(None, alias="t", description="One-time proxy token"),
    db: AsyncSession = Depends(get_db),
):
    """
    Proxy HTTPS request to the edge node through the reverse tunnel.

    This endpoint fetches content from the node's HTTPS service through
    the SSH tunnel container and returns it to the user.

    Authentication via one-time token (generated by POST /https-proxy-token).
    Token is single-use and expires after 60 seconds.
    """
    from fastapi.responses import HTMLResponse
    import ssl
    import aiohttp

    # Validate one-time token
    if not t:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token required. First call POST /https-proxy-token"
        )

    # Get and delete token from Redis (single-use)
    redis_client = await get_redis_client()
    token_key = f"proxy_token:{t}"
    token_data = await redis_client.get(token_key)

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    # Delete token immediately (single-use)
    await redis_client.delete(token_key)

    # Parse token data
    try:
        user_id, token_node_id = token_data.split(":")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token format")

    # Verify node_id matches
    if token_node_id != node_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token not valid for this node")

    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    current_user = result.scalar_one_or_none()
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # Get node
    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()

    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Node not found"
        )

    # Check node is online
    if node.status != NodeStatus.ONLINE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Node is {node.status.value}. Cannot connect to offline node."
        )

    # Check permissions
    if current_user.role != UserRole.SUPERUSER:
        accessible_node_ids = await GroupService.get_accessible_nodes_for_user(db, current_user)
        if node_id not in accessible_node_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this node"
            )

    # Get HTTPS port from application_ports
    https_port = None
    if node.application_ports and "HTTPS" in node.application_ports:
        https_port = node.application_ports["HTTPS"].get("remote")

    if not https_port:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="HTTPS service not configured for this node"
        )

    # Connect to SSH tunnel container
    ssh_tunnel_host = settings.SSH_TUNNEL_HOST
    target_url = f"https://{ssh_tunnel_host}:{https_port}"

    try:
        # Create SSL context that doesn't verify certificates (self-signed)
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        connector = aiohttp.TCPConnector(ssl=ssl_context)

        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(target_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                content = await response.text()

                logger.info(f"🌐 HTTPS proxy request to node {node.name} ({target_url})")

                return HTMLResponse(
                    content=content,
                    status_code=response.status,
                    headers={
                        "X-Orizon-Node": node.name,
                        "X-Orizon-Node-ID": node.id
                    }
                )

    except aiohttp.ClientConnectorError as e:
        logger.error(f"❌ HTTPS proxy connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cannot connect to node HTTPS service: {str(e)}"
        )
    except asyncio.TimeoutError:
        logger.error(f"❌ HTTPS proxy timeout for node {node.name}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Connection to node timed out"
        )
    except Exception as e:
        logger.error(f"❌ HTTPS proxy error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Proxy error: {str(e)}"
        )
