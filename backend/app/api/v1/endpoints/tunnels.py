"""
Orizon Zero Trust Connect - Tunnels API Endpoints
For: Marco @ Syneto/Orizon
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from loguru import logger

from app.core.database import get_db
from app.auth.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.services.tunnel_service import tunnel_service
from app.schemas.tunnel import (
    TunnelCreate,
    TunnelInfo,
    TunnelStatus,
    TunnelHealth
)
from app.middleware.rate_limit import rate_limit

router = APIRouter()


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

    Returns summary statistics and list of active tunnels
    """
    from sqlalchemy import select, func
    from app.models.node import Node, NodeStatus

    try:
        # Count nodes by status
        result = await db.execute(
            select(Node.status, func.count(Node.id))
            .group_by(Node.status)
        )
        status_counts = {str(row[0].value): row[1] for row in result.fetchall()}

        # Get online nodes with tunnel info
        result = await db.execute(
            select(Node)
            .where(Node.status == NodeStatus.ONLINE)
            .limit(50)
        )
        online_nodes = result.scalars().all()

        # Build active tunnels list
        active_tunnels = []
        for node in online_nodes:
            if node.application_ports:
                for app_name, ports in node.application_ports.items():
                    active_tunnels.append({
                        "tunnel_id": f"{node.id}_{app_name}",
                        "node_id": node.id,
                        "node_name": node.name,
                        "application": app_name,
                        "local_port": ports.get("local"),
                        "remote_port": ports.get("remote"),
                        "status": "active",
                        "connected_at": node.last_heartbeat.isoformat() if node.last_heartbeat else None
                    })

        return {
            "summary": {
                "total_nodes": sum(status_counts.values()),
                "online_nodes": status_counts.get("online", 0),
                "offline_nodes": status_counts.get("offline", 0),
                "active_tunnels": len(active_tunnels)
            },
            "tunnels": active_tunnels
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
    """
    try:
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
