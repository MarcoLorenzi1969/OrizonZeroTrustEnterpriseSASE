"""
Orizon Zero Trust Connect - Tunnels API Endpoints
For: Marco @ Syneto/Orizon
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import socket
import asyncio
from loguru import logger

from app.core.database import get_db
from app.auth.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.tunnel import Tunnel as TunnelModel
from app.services.tunnel_service import tunnel_service
from sqlalchemy import select
from app.schemas.tunnel import (
    TunnelCreate,
    TunnelInfo,
    TunnelStatus,
    TunnelHealth
)
from app.middleware.rate_limit import rate_limit

router = APIRouter()


def get_docker_host_ip() -> str:
    """Get the Docker host IP for port checking from within container"""
    try:
        # Try host.docker.internal first (works on Docker Desktop and with extra_hosts)
        import socket as sock_module
        result = sock_module.gethostbyname("host.docker.internal")
        return result
    except Exception:
        # Fallback to Docker default gateway
        return "172.18.0.1"


def check_port_open(port: int, host: str = None, timeout: float = 0.5) -> bool:
    """Check if a port is open and accepting connections on the host"""
    if host is None:
        host = get_docker_host_ip()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


async def check_port_open_async(port: int, host: str = None, timeout: float = 0.5) -> bool:
    """Async wrapper for port check"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, check_port_open, port, host, timeout)


# ============================================
# STATIC ROUTES FIRST (before dynamic routes)
# ============================================

@router.get("/dashboard")
async def get_tunnels_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get tunnels dashboard summary

    Returns summary statistics, system tunnels, and application tunnels
    Status is determined by real-time port accessibility check
    Only shows tunnels belonging to THIS hub (filtered by hub_host)
    """
    from sqlalchemy import select, func
    from sqlalchemy.orm import selectinload
    from app.models.node import Node, NodeStatus
    from app.models.tunnel import Tunnel, TunnelStatus as TunnelStatusEnum
    from app.core.config import settings
    from datetime import datetime, timedelta

    try:
        # Count nodes by status
        result = await db.execute(
            select(Node.status, func.count(Node.id))
            .group_by(Node.status)
        )
        status_counts = {str(row[0].value): row[1] for row in result.fetchall()}

        # Get all nodes with their tunnels
        result = await db.execute(
            select(Node).options(selectinload(Node.tunnels))
        )
        all_nodes = result.scalars().all()

        # Build system tunnels list (from tunnels table)
        system_tunnels = []
        application_tunnels = []

        # Collect all ports to check in parallel
        ports_to_check = []
        tunnel_port_map = {}

        # Get this hub's IP for filtering
        this_hub_host = settings.HUB_HOST
        logger.debug(f"Filtering tunnels for hub_host: {this_hub_host}")

        for node in all_nodes:
            # Process tunnels from database - only those belonging to this hub
            if node.tunnels:
                for tunnel in node.tunnels:
                    # Only include tunnels for THIS hub
                    if tunnel.hub_host == this_hub_host:
                        ports_to_check.append(tunnel.remote_port)
                        tunnel_port_map[tunnel.remote_port] = tunnel.id

            # Also collect application ports (these are hub-agnostic for now)
            if node.application_ports:
                for app_name, ports in node.application_ports.items():
                    if ports.get("remote"):
                        ports_to_check.append(ports.get("remote"))

        # Check all ports in parallel for performance
        port_status = {}
        if ports_to_check:
            check_tasks = [check_port_open_async(port) for port in ports_to_check]
            results = await asyncio.gather(*check_tasks, return_exceptions=True)
            for port, is_open in zip(ports_to_check, results):
                port_status[port] = is_open if isinstance(is_open, bool) else False

        # Keep-alive threshold for heartbeat-based fallback
        # Use timezone-naive comparison to avoid datetime comparison issues
        keepalive_threshold = datetime.utcnow() - timedelta(minutes=2)

        for node in all_nodes:
            # Check node heartbeat as secondary indicator
            # Handle both timezone-aware and naive datetimes
            node_has_recent_heartbeat = False
            if node.status == NodeStatus.ONLINE and node.last_heartbeat:
                try:
                    # Make both datetimes naive for comparison
                    hb = node.last_heartbeat.replace(tzinfo=None) if node.last_heartbeat.tzinfo else node.last_heartbeat
                    node_has_recent_heartbeat = hb > keepalive_threshold
                except Exception:
                    node_has_recent_heartbeat = False

            # Process tunnels from database - only those belonging to this hub
            if node.tunnels:
                for tunnel in node.tunnels:
                    # Skip tunnels not belonging to this hub
                    if tunnel.hub_host != this_hub_host:
                        continue

                    # Primary: check if port is actually accessible
                    port_is_open = port_status.get(tunnel.remote_port, False)

                    # Tunnel is active if port is open OR node has recent heartbeat
                    is_active = port_is_open or node_has_recent_heartbeat

                    tunnel_data = {
                        "tunnel_id": tunnel.id,
                        "node_id": node.id,
                        "node_name": node.name,
                        "name": tunnel.name,
                        "tunnel_type": tunnel.tunnel_type.value if tunnel.tunnel_type else "ssh",
                        "local_port": tunnel.local_port,
                        "remote_port": tunnel.remote_port,
                        "hub_host": tunnel.hub_host,
                        "hub_port": tunnel.hub_port,
                        "is_system": tunnel.is_system,
                        "status": "active" if is_active else "inactive",
                        "port_accessible": port_is_open,
                        "health_status": "healthy" if is_active else "unhealthy",
                        "last_heartbeat": node.last_heartbeat.isoformat() if node.last_heartbeat else None,
                        "created_at": tunnel.created_at.isoformat() if tunnel.created_at else None,
                        "connected_at": tunnel.last_connected_at.isoformat() if tunnel.last_connected_at else None
                    }

                    if tunnel.is_system:
                        system_tunnels.append(tunnel_data)
                    else:
                        application_tunnels.append(tunnel_data)

            # Also add application ports (legacy format) as application tunnels
            if node.application_ports and node.status == NodeStatus.ONLINE:
                for app_name, ports in node.application_ports.items():
                    remote_port = ports.get("remote")
                    port_is_open = port_status.get(remote_port, False) if remote_port else False
                    is_active = port_is_open or node_has_recent_heartbeat

                    application_tunnels.append({
                        "tunnel_id": f"{node.id}_{app_name}",
                        "node_id": node.id,
                        "node_name": node.name,
                        "name": f"{app_name} Tunnel",
                        "tunnel_type": "ssh",
                        "application": app_name,
                        "local_port": ports.get("local"),
                        "remote_port": remote_port,
                        "is_system": False,
                        "status": "active" if is_active else "inactive",
                        "port_accessible": port_is_open,
                        "health_status": "healthy" if is_active else "unhealthy",
                        "last_heartbeat": node.last_heartbeat.isoformat() if node.last_heartbeat else None,
                        "connected_at": node.last_heartbeat.isoformat() if node.last_heartbeat else None
                    })

        # Count healthy/unhealthy system tunnels
        healthy_system_tunnels = sum(1 for t in system_tunnels if t["health_status"] == "healthy")
        unhealthy_system_tunnels = len(system_tunnels) - healthy_system_tunnels

        return {
            "summary": {
                "total_nodes": sum(status_counts.values()),
                "online_nodes": status_counts.get("online", 0),
                "offline_nodes": status_counts.get("offline", 0),
                "system_tunnels": len(system_tunnels),
                "system_tunnels_healthy": healthy_system_tunnels,
                "system_tunnels_unhealthy": unhealthy_system_tunnels,
                "application_tunnels": len(application_tunnels),
                "active_tunnels": healthy_system_tunnels + sum(1 for t in application_tunnels if t["health_status"] == "healthy")
            },
            "system_tunnels": system_tunnels,
            "tunnels": application_tunnels
        }

    except Exception as e:
        logger.error(f"❌ Error getting tunnels dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/health/all", response_model=List[TunnelHealth])
async def get_all_tunnels_health(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    Get health status of all tunnels

    Requires: Admin role or higher
    """
    try:
        health_results = await tunnel_service.health_check_all_tunnels(db)
        return health_results

    except Exception as e:
        logger.error(f"❌ Error getting tunnels health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================
# POST/DELETE routes
# ============================================

@router.post("/", response_model=TunnelInfo, status_code=status.HTTP_201_CREATED)
@rate_limit("20/minute")
async def create_tunnel(
    request: Request,
    tunnel_data: TunnelCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    Create new tunnel (SSH or HTTPS)

    Requires: Admin role or higher
    """
    try:
        # Determine tunnel type and create
        if tunnel_data.tunnel_type == "ssh":
            tunnel = await tunnel_service.create_ssh_tunnel(
                db=db,
                node_id=tunnel_data.node_id,
                agent_public_key=tunnel_data.agent_public_key,
                agent_ip=tunnel_data.agent_ip
            )
        elif tunnel_data.tunnel_type == "https":
            tunnel = await tunnel_service.create_https_tunnel(
                db=db,
                node_id=tunnel_data.node_id,
                cert_data=tunnel_data.cert_data,
                agent_ip=tunnel_data.agent_ip
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tunnel type: {tunnel_data.tunnel_type}"
            )

        if not tunnel:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create tunnel"
            )

        logger.info(f"✅ Tunnel created via API: {tunnel.tunnel_id} by {current_user.email}")

        return tunnel

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating tunnel: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{tunnel_id}", status_code=status.HTTP_204_NO_CONTENT)
@rate_limit("10/minute")
async def close_tunnel(
    request: Request,
    tunnel_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    Close and cleanup tunnel

    Requires: Admin role or higher

    Note: System tunnels (is_system=True) cannot be deleted via API.
    They are automatically deleted when the associated node is deleted.
    """
    try:
        # Check if this is a system tunnel
        result = await db.execute(
            select(TunnelModel).where(TunnelModel.id == tunnel_id)
        )
        tunnel = result.scalar_one_or_none()

        if not tunnel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tunnel {tunnel_id} not found"
            )

        # Protect system tunnels from deletion
        if tunnel.is_system:
            logger.warning(f"⛔ Attempted to delete system tunnel {tunnel_id} by {current_user.email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete system tunnel. Delete the associated node to remove this tunnel."
            )

        success = await tunnel_service.close_tunnel(db, tunnel_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tunnel {tunnel_id} not found"
            )

        logger.info(f"✅ Tunnel closed via API: {tunnel_id} by {current_user.email}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error closing tunnel: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================
# DYNAMIC ROUTES LAST
# ============================================

@router.get("/{tunnel_id}", response_model=TunnelStatus)
async def get_tunnel_status(
    tunnel_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get tunnel status

    Requires: Any authenticated user
    """
    try:
        tunnel_status = await tunnel_service.get_tunnel_status(db, tunnel_id)

        if not tunnel_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tunnel {tunnel_id} not found"
            )

        return tunnel_status

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting tunnel status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
