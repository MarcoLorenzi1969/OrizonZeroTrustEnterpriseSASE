"""
Orizon Guacamole API Endpoints
FastAPI endpoints for Guacamole SSO integration
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import logging
import asyncpg
from uuid import UUID

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/guacamole", tags=["guacamole"])


# Pydantic Models
class GuacamoleConnectionCreate(BaseModel):
    node_id: UUID
    protocol: str = Field(..., pattern="^(ssh|rdp|vnc)$")
    connection_name: Optional[str] = None


class GuacamoleConnectionInfo(BaseModel):
    id: UUID
    node_id: UUID
    connection_id: str
    connection_name: str
    protocol: str
    status: str
    access_url: str
    created_at: datetime


class GuacamoleSessionInfo(BaseModel):
    session_id: UUID
    guacamole_token: str
    connection_url: str
    expires_at: datetime


class NodeConnectionsResponse(BaseModel):
    node_id: UUID
    node_name: str
    connections: List[Dict]


# Dependency to get database connection
async def get_db():
    """Get database connection"""
    import os
    conn = await asyncpg.connect(
        host=os.getenv('ORIZON_DB_HOST', '46.101.189.126'),
        port=int(os.getenv('ORIZON_DB_PORT', 5432)),
        user=os.getenv('ORIZON_DB_USER', 'postgres'),
        password=os.getenv('ORIZON_DB_PASS', ''),  # Set in environment
        database=os.getenv('ORIZON_DB_NAME', 'orizon_ztc')
    )
    try:
        yield conn
    finally:
        await conn.close()


# Dependency to get Guacamole service
async def get_guac_service():
    """Get Guacamole SSO service instance"""
    from .guacamole_sso_service import GuacamoleSSO
    import os

    service = GuacamoleSSO(
        guac_url=os.getenv('GUAC_URL', 'https://167.71.33.70/guacamole'),
        guac_datasource=os.getenv('GUAC_DATASOURCE', 'mysql'),
        guac_admin_user=os.getenv('GUAC_ADMIN_USER', 'orizonzerotrust'),
        guac_admin_pass=os.getenv('GUAC_ADMIN_PASS', 'ripper-FfFIlBelloccio.1969F-web'),
        verify_ssl=os.getenv('GUAC_VERIFY_TLS', 'false').lower() == 'true'
    )
    return service


@router.get("/health")
async def health_check(guac_service=Depends(get_guac_service)):
    """Check Guacamole server health"""
    try:
        is_healthy = await guac_service.health_check()
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )


@router.post("/sso/authenticate")
async def sso_authenticate(
    current_user: dict,  # From Orizon JWT
    guac_service=Depends(get_guac_service),
    db=Depends(get_db)
):
    """
    Authenticate user via SSO and get Guacamole token
    Requires Orizon JWT authentication
    """
    try:
        # Get Guacamole credentials for user
        guac_creds = await guac_service.authenticate_user(
            orizon_user_email=current_user['email'],
            orizon_user_role=current_user['role']
        )

        # Get Guacamole token
        token_info = await guac_service.get_user_token(
            guac_creds['username'],
            guac_creds['password']
        )

        # Store session in database
        session_id = await db.fetchval("""
            INSERT INTO guacamole_sessions (
                user_id, guacamole_server_id, guacamole_token, expires_at
            ) VALUES (
                $1,
                (SELECT id FROM guacamole_servers WHERE name = 'Primary Guacamole Hub'),
                $2,
                $3
            ) RETURNING id
        """, UUID(current_user['id']), token_info['authToken'], datetime.utcnow() + timedelta(hours=1))

        # Log access
        await db.execute("""
            INSERT INTO guacamole_access_logs (
                user_id, action, success, ip_address
            ) VALUES ($1, 'sso_login', true, $2)
        """, UUID(current_user['id']), current_user.get('ip'))

        return {
            "session_id": str(session_id),
            "guacamole_token": token_info['authToken'],
            "username": token_info['username'],
            "datasource": token_info['dataSource'],
            "expires_in": 3600
        }

    except Exception as e:
        logger.error(f"SSO authentication error: {e}")
        # Log failed attempt
        try:
            await db.execute("""
                INSERT INTO guacamole_access_logs (
                    user_id, action, success, error_message
                ) VALUES ($1, 'sso_login', false, $2)
            """, UUID(current_user.get('id')), str(e))
        except:
            pass

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/nodes/{node_id}/connections", response_model=GuacamoleConnectionInfo)
async def create_node_connection(
    node_id: UUID,
    connection_data: GuacamoleConnectionCreate,
    current_user: dict,
    guac_service=Depends(get_guac_service),
    db=Depends(get_db)
):
    """Create Guacamole connection for a node"""
    try:
        # Get node information
        node = await db.fetchrow("""
            SELECT id, name, ip_address, ssh_port, rdp_port
            FROM nodes
            WHERE id = $1
        """, node_id)

        if not node:
            raise HTTPException(status_code=404, detail="Node not found")

        # Determine connection parameters based on protocol
        if connection_data.protocol == 'ssh':
            port = node['ssh_port'] or 22
            extra_params = {
                'enable-sftp': 'true',
                'term-type': 'xterm-256color'
            }
        elif connection_data.protocol == 'rdp':
            port = node['rdp_port'] or 3389
            extra_params = {
                'security': 'any',
                'ignore-cert': 'true',
                'enable-drive': 'false',
                'enable-clipboard': 'false'
            }
        else:
            port = 5900  # VNC default
            extra_params = {}

        # Create connection in Guacamole
        connection_name = connection_data.connection_name or f"{node['name']} - {connection_data.protocol.upper()}"
        guac_conn = await guac_service.create_connection(
            name=connection_name,
            protocol=connection_data.protocol,
            hostname=node['ip_address'],
            port=port,
            username='parallels',  # TODO: Get from node config
            password='profano.69',   # TODO: Get from secure store
            **extra_params
        )

        # Store in database
        conn_id = await db.fetchval("""
            INSERT INTO guacamole_connections (
                node_id,
                guacamole_server_id,
                connection_id,
                connection_name,
                protocol,
                status
            ) VALUES (
                $1,
                (SELECT id FROM guacamole_servers WHERE name = 'Primary Guacamole Hub'),
                $2,
                $3,
                $4,
                'active'
            ) RETURNING id
        """, node_id, guac_conn['identifier'], connection_name, connection_data.protocol)

        # Get Guacamole server URL
        guac_url = await db.fetchval("""
            SELECT url FROM guacamole_servers WHERE name = 'Primary Guacamole Hub'
        """)

        return GuacamoleConnectionInfo(
            id=conn_id,
            node_id=node_id,
            connection_id=guac_conn['identifier'],
            connection_name=connection_name,
            protocol=connection_data.protocol,
            status='active',
            access_url=f"{guac_url}/#/client/{guac_conn['identifier']}",
            created_at=datetime.utcnow()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/nodes/{node_id}/connections", response_model=NodeConnectionsResponse)
async def get_node_connections(
    node_id: UUID,
    current_user: dict,
    db=Depends(get_db)
):
    """Get all Guacamole connections for a node"""
    try:
        # Get node info
        node = await db.fetchrow("SELECT name FROM nodes WHERE id = $1", node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Node not found")

        # Get connections
        connections = await db.fetch("""
            SELECT
                gc.id,
                gc.connection_id,
                gc.connection_name,
                gc.protocol,
                gc.status,
                gc.created_at,
                gs.url as guac_url
            FROM guacamole_connections gc
            JOIN guacamole_servers gs ON gc.guacamole_server_id = gs.id
            WHERE gc.node_id = $1
            ORDER BY gc.created_at DESC
        """, node_id)

        return NodeConnectionsResponse(
            node_id=node_id,
            node_name=node['name'],
            connections=[
                {
                    "id": str(conn['id']),
                    "connection_id": conn['connection_id'],
                    "connection_name": conn['connection_name'],
                    "protocol": conn['protocol'],
                    "status": conn['status'],
                    "access_url": f"{conn['guac_url']}/#/client/{conn['connection_id']}",
                    "created_at": conn['created_at'].isoformat()
                }
                for conn in connections
            ]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting connections: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/nodes/{node_id}/access/{protocol}")
async def quick_access_node(
    node_id: UUID,
    protocol: str,
    current_user: dict,
    guac_service=Depends(get_guac_service),
    db=Depends(get_db)
):
    """Quick access to node via Guacamole (creates connection if not exists)"""
    try:
        # Check if connection already exists
        existing = await db.fetchrow("""
            SELECT
                gc.id,
                gc.connection_id,
                gs.url as guac_url
            FROM guacamole_connections gc
            JOIN guacamole_servers gs ON gc.guacamole_server_id = gs.id
            WHERE gc.node_id = $1 AND gc.protocol = $2
        """, node_id, protocol)

        if existing:
            connection_id = existing['connection_id']
            guac_url = existing['guac_url']
        else:
            # Create connection
            conn_data = GuacamoleConnectionCreate(
                node_id=node_id,
                protocol=protocol
            )
            new_conn = await create_node_connection(
                node_id, conn_data, current_user, guac_service, db
            )
            connection_id = new_conn.connection_id
            guac_url = new_conn.access_url.split('/#/')[0]

        # Get user's Guacamole token
        guac_creds = await guac_service.authenticate_user(
            orizon_user_email=current_user['email'],
            orizon_user_role=current_user['role']
        )
        token_info = await guac_service.get_user_token(
            guac_creds['username'],
            guac_creds['password']
        )

        # Log access
        await db.execute("""
            INSERT INTO guacamole_access_logs (
                user_id, connection_id, action, success
            ) VALUES (
                $1,
                (SELECT id FROM guacamole_connections WHERE connection_id = $2),
                'access_connection',
                true
            )
        """, UUID(current_user['id']), connection_id)

        return {
            "connection_id": connection_id,
            "access_url": f"{guac_url}/#/client/{connection_id}?token={token_info['authToken']}",
            "guacamole_token": token_info['authToken'],
            "protocol": protocol
        }

    except Exception as e:
        logger.error(f"Quick access error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/connections")
async def list_all_connections(
    current_user: dict,
    guac_service=Depends(get_guac_service)
):
    """List all Guacamole connections"""
    try:
        connections = await guac_service.get_connections()
        return connections
    except Exception as e:
        logger.error(f"Error listing connections: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/connections/{connection_id}")
async def delete_connection(
    connection_id: str,
    current_user: dict,
    guac_service=Depends(get_guac_service),
    db=Depends(get_db)
):
    """Delete a Guacamole connection"""
    try:
        # Delete from Guacamole
        await guac_service.delete_connection(connection_id)

        # Delete from database
        await db.execute("""
            DELETE FROM guacamole_connections
            WHERE connection_id = $1
        """, connection_id)

        return {"message": "Connection deleted successfully"}

    except Exception as e:
        logger.error(f"Error deleting connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
