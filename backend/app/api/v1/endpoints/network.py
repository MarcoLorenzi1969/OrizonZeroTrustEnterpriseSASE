"""
Orizon Zero Trust Connect - Network Topology API Endpoints
For: Marco @ Syneto/Orizon
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Dict, List, Any
from loguru import logger

from app.core.database import get_db
from app.core.redis import redis_client
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.node import Node, NodeStatus, NodeType, ExposedApplication

router = APIRouter()

# Redis key for storing node positions
NODE_POSITIONS_KEY = "network:node_positions"
HUB_NODE_ID = "hub-orizon-central"


@router.get("/topology")
async def get_network_topology(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get network topology with nodes and edges for visualization.

    Returns:
    - nodes: List of nodes (including hub)
    - edges: Connections between hub and nodes
    - stats: Network statistics
    """
    try:
        # Get all nodes from database
        result = await db.execute(select(Node))
        db_nodes = result.scalars().all()

        # Build nodes list - start with the HUB
        nodes = []

        # Add Hub node (central node)
        nodes.append({
            "id": HUB_NODE_ID,
            "label": "Orizon Hub",
            "type": "hub",
            "status": "online",
            "ip_address": "139.59.149.48",
            "agent_connected": True,
            "description": "Central Hub - Zero Trust Controller",
            "services": ["SSH Tunnel Server", "API Gateway", "Auth Server"],
            "rdp_available": False,
            "ssh_available": True
        })

        # Add edge nodes
        for node in db_nodes:
            # Determine available services
            services = []
            rdp_available = False
            ssh_available = False

            if node.exposed_applications:
                for app in node.exposed_applications:
                    services.append(app)
                    if app == "RDP":
                        rdp_available = True
                    if app == "TERMINAL":
                        ssh_available = True

            # Default: terminal always available for linux/macos
            if node.node_type in [NodeType.LINUX, NodeType.MACOS]:
                ssh_available = True
                if "TERMINAL" not in services:
                    services.append("TERMINAL")

            nodes.append({
                "id": str(node.id),
                "label": node.name,
                "type": node.node_type.value if node.node_type else "linux",
                "status": node.status.value if node.status else "offline",
                "ip_address": node.public_ip or node.private_ip or "N/A",
                "agent_connected": node.status == NodeStatus.ONLINE,
                "description": node.location or f"{node.hostname}",
                "services": services,
                "rdp_available": rdp_available,
                "ssh_available": ssh_available
            })

        # Build edges - connections between hub and each node
        edges = []
        for node in db_nodes:
            is_online = node.status == NodeStatus.ONLINE

            # Get bandwidth from recent metrics (stored in custom_metadata)
            bandwidth = node.custom_metadata.get("bandwidth", {}) if node.custom_metadata else {}

            # Build services list for edge
            edge_services = []
            if node.application_ports:
                for app_name in node.application_ports.keys():
                    edge_services.append(app_name)

            edges.append({
                "from": HUB_NODE_ID,
                "to": str(node.id),
                "label": "Reverse Tunnel" if is_online else "Disconnected",
                "services": edge_services if edge_services else ["Tunnel"],
                "connection_quality": "good" if is_online else "none",
                "status": "active" if is_online else "inactive",
                "bandwidth": {
                    "in": bandwidth.get("in", 0),
                    "out": bandwidth.get("out", 0),
                    "total": bandwidth.get("total", 0),
                    "usage_percent": bandwidth.get("usage_percent", 0)
                }
            })

        # Calculate stats
        total_nodes = len(db_nodes)
        online_nodes = sum(1 for n in db_nodes if n.status == NodeStatus.ONLINE)
        offline_nodes = sum(1 for n in db_nodes if n.status == NodeStatus.OFFLINE)
        degraded_nodes = sum(1 for n in db_nodes if n.status == NodeStatus.DEGRADED)

        stats = {
            "total_nodes": total_nodes + 1,  # +1 for hub
            "online_nodes": online_nodes + 1,  # Hub is always online
            "offline_nodes": offline_nodes,
            "degraded_nodes": degraded_nodes,
            "active_tunnels": online_nodes,
            "total_services": sum(len(n.exposed_applications or []) for n in db_nodes)
        }

        return {
            "nodes": nodes,
            "edges": edges,
            "stats": stats
        }

    except Exception as e:
        logger.error(f"❌ Error getting network topology: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/node-positions")
async def get_node_positions(
    current_user: User = Depends(get_current_user)
):
    """
    Get saved node positions for the network map.
    Positions are stored in Redis for fast access.
    """
    try:
        positions_json = await redis_client.get(NODE_POSITIONS_KEY)

        if positions_json:
            import json
            positions = json.loads(positions_json)
        else:
            positions = {}

        return {"positions": positions}

    except Exception as e:
        logger.error(f"❌ Error getting node positions: {e}")
        return {"positions": {}}


@router.post("/node-positions")
async def save_node_positions(
    positions: Dict[str, Dict[str, float]],
    current_user: User = Depends(get_current_user)
):
    """
    Save node positions for the network map.
    Positions are stored in Redis.

    Expected format:
    {
        "node-id-1": {"x": 100, "y": 200},
        "node-id-2": {"x": 300, "y": 400}
    }
    """
    try:
        import json

        # Load existing positions
        existing_json = await redis_client.get(NODE_POSITIONS_KEY)
        if existing_json:
            existing = json.loads(existing_json)
        else:
            existing = {}

        # Merge with new positions
        existing.update(positions)

        # Save to Redis (expire after 30 days)
        await redis_client.set(
            NODE_POSITIONS_KEY,
            json.dumps(existing),
            ex=30 * 24 * 60 * 60  # 30 days
        )

        logger.info(f"✅ Saved {len(positions)} node positions by {current_user.email}")

        return {
            "status": "success",
            "saved_count": len(positions),
            "total_positions": len(existing)
        }

    except Exception as e:
        logger.error(f"❌ Error saving node positions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/stats")
async def get_network_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed network statistics.
    """
    try:
        # Count nodes by status
        result = await db.execute(
            select(Node.status, func.count(Node.id))
            .group_by(Node.status)
        )
        status_counts = {str(row[0].value): row[1] for row in result.fetchall()}

        # Count nodes by type
        result = await db.execute(
            select(Node.node_type, func.count(Node.id))
            .group_by(Node.node_type)
        )
        type_counts = {str(row[0].value): row[1] for row in result.fetchall()}

        # Get average resource usage from online nodes
        result = await db.execute(
            select(
                func.avg(Node.cpu_usage),
                func.avg(Node.memory_usage),
                func.avg(Node.disk_usage)
            ).where(Node.status == NodeStatus.ONLINE)
        )
        row = result.fetchone()

        return {
            "by_status": status_counts,
            "by_type": type_counts,
            "resource_usage": {
                "avg_cpu": round(row[0] or 0, 2),
                "avg_memory": round(row[1] or 0, 2),
                "avg_disk": round(row[2] or 0, 2)
            },
            "total_nodes": sum(status_counts.values()),
            "online_nodes": status_counts.get("online", 0)
        }

    except Exception as e:
        logger.error(f"❌ Error getting network stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
