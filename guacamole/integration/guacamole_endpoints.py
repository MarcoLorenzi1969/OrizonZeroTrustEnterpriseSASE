"""
Orizon Zero Trust Connect - Guacamole API Endpoints

Add these endpoints to backend/app/api/v1/endpoints/
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel
import logging

from app.db.database import get_db
from app.auth.security import get_current_user
from guacamole.integration.guacamole_service import (
    GuacamoleIntegrationService,
    GuacamoleAPIClient
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/guacamole", tags=["guacamole"])


# Configuration (should come from environment)
GUACAMOLE_URL = "https://167.71.33.70"
GUACAMOLE_USERNAME = "guacadmin"
GUACAMOLE_PASSWORD = "guacadmin"  # Change in production!


# Pydantic models
class GuacamoleConnection(BaseModel):
    """Guacamole connection model"""
    id: str
    name: str
    protocol: str
    hostname: str
    port: int
    node_id: Optional[str] = None


class CreateSSHConnectionRequest(BaseModel):
    """Request to create SSH connection"""
    node_id: str
    name: Optional[str] = None
    username: str
    password: Optional[str] = None
    private_key: Optional[str] = None


class CreateRDPConnectionRequest(BaseModel):
    """Request to create RDP connection"""
    node_id: str
    name: Optional[str] = None
    username: str
    password: str
    domain: Optional[str] = None


class GuacamoleAccessURLResponse(BaseModel):
    """Response with Guacamole access URL"""
    url: str
    connection_id: str
    protocol: str


@router.get("/status")
async def get_guacamole_status(
    current_user: dict = Depends(get_current_user)
):
    """
    Check Guacamole server status

    Returns:
        Guacamole server status and version
    """
    try:
        async with GuacamoleAPIClient(
            GUACAMOLE_URL,
            GUACAMOLE_USERNAME,
            GUACAMOLE_PASSWORD
        ) as client:
            # Try to authenticate
            token = await client.authenticate()

            return {
                "status": "online",
                "url": GUACAMOLE_URL,
                "authenticated": True,
                "message": "Guacamole hub is operational"
            }
    except Exception as e:
        logger.error(f"Guacamole health check failed: {e}")
        return {
            "status": "offline",
            "url": GUACAMOLE_URL,
            "authenticated": False,
            "error": str(e)
        }


@router.get("/connections")
async def list_guacamole_connections(
    current_user: dict = Depends(get_current_user)
) -> List[GuacamoleConnection]:
    """
    List all Guacamole connections

    Returns:
        List of Guacamole connections
    """
    try:
        async with GuacamoleAPIClient(
            GUACAMOLE_URL,
            GUACAMOLE_USERNAME,
            GUACAMOLE_PASSWORD
        ) as client:
            connections = await client.list_connections()

            return [
                GuacamoleConnection(
                    id=conn.get("identifier"),
                    name=conn.get("name"),
                    protocol=conn.get("protocol"),
                    hostname=conn.get("parameters", {}).get("hostname", ""),
                    port=int(conn.get("parameters", {}).get("port", 0))
                )
                for conn in connections
            ]
    except Exception as e:
        logger.error(f"Failed to list connections: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list connections: {str(e)}"
        )


@router.post("/connections/ssh")
async def create_ssh_connection(
    request: CreateSSHConnectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> GuacamoleConnection:
    """
    Create SSH connection in Guacamole for an Orizon node

    Args:
        request: SSH connection creation request
        db: Database session
        current_user: Current authenticated user

    Returns:
        Created Guacamole connection
    """
    # Get node details
    result = await db.execute(
        text("SELECT id, name, ip_address FROM nodes WHERE id = :id"),
        {"id": request.node_id}
    )
    node = result.fetchone()

    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node {request.node_id} not found"
        )

    try:
        async with GuacamoleAPIClient(
            GUACAMOLE_URL,
            GUACAMOLE_USERNAME,
            GUACAMOLE_PASSWORD
        ) as client:
            # Create connection
            connection = await client.create_ssh_connection(
                name=request.name or f"Orizon - {node.name}",
                hostname=node.ip_address or "10.211.55.19",
                port=22,
                username=request.username,
                password=request.password,
                private_key=request.private_key
            )

            # Save connection ID in database
            await db.execute(
                text("""
                    UPDATE nodes
                    SET guacamole_connection_id = :conn_id
                    WHERE id = :node_id
                """),
                {
                    "conn_id": connection["identifier"],
                    "node_id": request.node_id
                }
            )
            await db.commit()

            return GuacamoleConnection(
                id=connection["identifier"],
                name=connection["name"],
                protocol="ssh",
                hostname=node.ip_address,
                port=22,
                node_id=request.node_id
            )

    except Exception as e:
        logger.error(f"Failed to create SSH connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create SSH connection: {str(e)}"
        )


@router.post("/connections/rdp")
async def create_rdp_connection(
    request: CreateRDPConnectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> GuacamoleConnection:
    """
    Create RDP connection in Guacamole for an Orizon node

    Args:
        request: RDP connection creation request
        db: Database session
        current_user: Current authenticated user

    Returns:
        Created Guacamole connection
    """
    # Get node details
    result = await db.execute(
        text("SELECT id, name, ip_address FROM nodes WHERE id = :id"),
        {"id": request.node_id}
    )
    node = result.fetchone()

    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node {request.node_id} not found"
        )

    try:
        async with GuacamoleAPIClient(
            GUACAMOLE_URL,
            GUACAMOLE_USERNAME,
            GUACAMOLE_PASSWORD
        ) as client:
            # Create connection
            connection = await client.create_rdp_connection(
                name=request.name or f"Orizon RDP - {node.name}",
                hostname=node.ip_address,
                port=3389,
                username=request.username,
                password=request.password,
                domain=request.domain
            )

            # Save connection ID in database
            await db.execute(
                text("""
                    UPDATE nodes
                    SET guacamole_rdp_connection_id = :conn_id
                    WHERE id = :node_id
                """),
                {
                    "conn_id": connection["identifier"],
                    "node_id": request.node_id
                }
            )
            await db.commit()

            return GuacamoleConnection(
                id=connection["identifier"],
                name=connection["name"],
                protocol="rdp",
                hostname=node.ip_address,
                port=3389,
                node_id=request.node_id
            )

    except Exception as e:
        logger.error(f"Failed to create RDP connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create RDP connection: {str(e)}"
        )


@router.get("/nodes/{node_id}/access-url")
async def get_node_access_url(
    node_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> GuacamoleAccessURLResponse:
    """
    Get Guacamole web access URL for a node

    Args:
        node_id: Node ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Guacamole access URL
    """
    # Get node with Guacamole connection ID
    result = await db.execute(
        text("""
            SELECT id, name, ip_address, guacamole_connection_id
            FROM nodes
            WHERE id = :id
        """),
        {"id": node_id}
    )
    node = result.fetchone()

    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node {node_id} not found"
        )

    # If no connection ID, create one
    if not node.guacamole_connection_id:
        # Auto-create SSH connection with default credentials
        async with GuacamoleAPIClient(
            GUACAMOLE_URL,
            GUACAMOLE_USERNAME,
            GUACAMOLE_PASSWORD
        ) as client:
            connection = await client.create_ssh_connection(
                name=f"Orizon - {node.name}",
                hostname=node.ip_address or "10.211.55.19",
                port=22,
                username="parallels",  # Default
                password="profano.69"  # Should be from secure storage
            )

            conn_id = connection["identifier"]

            # Save to database
            await db.execute(
                text("""
                    UPDATE nodes
                    SET guacamole_connection_id = :conn_id
                    WHERE id = :node_id
                """),
                {"conn_id": conn_id, "node_id": node_id}
            )
            await db.commit()
    else:
        conn_id = node.guacamole_connection_id

    # Build access URL
    url = f"{GUACAMOLE_URL}/guacamole/#/client/{conn_id}"

    return GuacamoleAccessURLResponse(
        url=url,
        connection_id=conn_id,
        protocol="ssh"
    )


@router.delete("/connections/{connection_id}")
async def delete_connection(
    connection_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete Guacamole connection

    Args:
        connection_id: Guacamole connection ID
        current_user: Current authenticated user

    Returns:
        Success message
    """
    try:
        async with GuacamoleAPIClient(
            GUACAMOLE_URL,
            GUACAMOLE_USERNAME,
            GUACAMOLE_PASSWORD
        ) as client:
            await client.delete_connection(connection_id)

        return {"message": f"Connection {connection_id} deleted successfully"}

    except Exception as e:
        logger.error(f"Failed to delete connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete connection: {str(e)}"
        )


@router.post("/sync-all-nodes")
async def sync_all_nodes(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Sync all Orizon nodes to Guacamole as SSH connections

    Args:
        db: Database session
        current_user: Current authenticated user

    Returns:
        Sync result with count
    """
    service = GuacamoleIntegrationService(
        GUACAMOLE_URL,
        GUACAMOLE_USERNAME,
        GUACAMOLE_PASSWORD,
        db
    )

    try:
        synced_count = await service.sync_all_nodes()

        return {
            "message": f"Successfully synced {synced_count} nodes to Guacamole",
            "synced_count": synced_count
        }

    except Exception as e:
        logger.error(f"Failed to sync nodes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync nodes: {str(e)}"
        )


@router.get("/active-sessions")
async def get_active_sessions(
    current_user: dict = Depends(get_current_user)
):
    """
    Get list of active Guacamole sessions

    Args:
        current_user: Current authenticated user

    Returns:
        List of active sessions
    """
    try:
        async with GuacamoleAPIClient(
            GUACAMOLE_URL,
            GUACAMOLE_USERNAME,
            GUACAMOLE_PASSWORD
        ) as client:
            sessions = await client.get_active_sessions()

            return {
                "active_sessions": len(sessions),
                "sessions": sessions
            }

    except Exception as e:
        logger.error(f"Failed to get active sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get active sessions: {str(e)}"
        )
