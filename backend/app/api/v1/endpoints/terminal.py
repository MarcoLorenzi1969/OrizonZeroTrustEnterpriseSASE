"""
Orizon Zero Trust Connect - Terminal WebSocket Endpoint
Interactive SSH terminal via WebSocket with full session recording

For: Marco @ Syneto/Orizon
"""

import json
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError
from loguru import logger

from app.core.database import get_db
from app.core.config import settings
from app.core.mongodb import mongodb_client
from app.models.user import User, UserRole
from app.models.node import Node, NodeStatus
from app.services.group_service import GroupService
from app.terminal.ssh_bridge import SSHBridge
from app.terminal.session_recorder import SessionRecorder, SessionManager

router = APIRouter()

# Global session manager
session_manager: Optional[SessionManager] = None


async def get_session_manager() -> SessionManager:
    """Get or create session manager."""
    global session_manager
    if session_manager is None:
        session_manager = SessionManager(mongodb_client.db)
    return session_manager


async def authenticate_websocket(token: str, db: AsyncSession) -> Optional[User]:
    """Validate JWT token and return user."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("sub")
        if not user_id:
            return None

        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        return None


async def check_node_access(
    user: User,
    node_id: str,
    db: AsyncSession
) -> tuple[bool, Optional[Node], str]:
    """Check if user has access to node."""
    # Get node
    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()

    if not node:
        return False, None, "Node not found"

    # SuperUser has access to all nodes
    if user.role == UserRole.SUPERUSER:
        return True, node, ""

    # Check group-based access
    accessible_node_ids = await GroupService.get_accessible_nodes_for_user(db, user)
    if node_id not in accessible_node_ids:
        return False, None, "Not authorized to access this node"

    return True, node, ""


def get_client_ip(websocket: WebSocket) -> str:
    """Extract client IP from WebSocket."""
    # Check for forwarded headers (behind proxy)
    forwarded = websocket.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = websocket.headers.get("x-real-ip")
    if real_ip:
        return real_ip

    # Fallback to direct client
    if websocket.client:
        return websocket.client.host

    return "unknown"


@router.websocket("/{node_id}")
async def terminal_websocket(
    websocket: WebSocket,
    node_id: str,
    token: Optional[str] = Query(None),
):
    """
    WebSocket endpoint for interactive SSH terminal.

    Protocol:
    1. Client connects with JWT token in query param: ?token=JWT
    2. Server validates token and node access
    3. Server connects to node via reverse tunnel
    4. Bidirectional communication:
       - Client sends: {"type": "input", "data": "..."} or {"type": "resize", "cols": N, "rows": N}
       - Server sends: {"type": "output", "data": "..."} or {"type": "error", "message": "..."}

    Full session recording is saved to MongoDB for audit compliance.
    """
    await websocket.accept()

    # Get database session
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        # === Phase 1: Authentication ===
        if not token:
            # Try to receive auth message
            try:
                raw_message = await websocket.receive_text()
                message = json.loads(raw_message)
                if message.get("type") == "auth":
                    token = message.get("token")
            except Exception:
                pass

        if not token:
            await websocket.send_json({
                "type": "error",
                "message": "Authentication required. Send token in query param or auth message."
            })
            await websocket.close(code=4001, reason="Authentication required")
            return

        user = await authenticate_websocket(token, db)
        if not user:
            await websocket.send_json({
                "type": "error",
                "message": "Invalid or expired token"
            })
            await websocket.close(code=4001, reason="Invalid token")
            return

        logger.info(f"Terminal WebSocket authenticated: user={user.email}")

        # === Phase 2: Authorization ===
        has_access, node, error_msg = await check_node_access(user, node_id, db)
        if not has_access:
            await websocket.send_json({
                "type": "error",
                "message": error_msg
            })
            await websocket.close(code=4003, reason=error_msg)
            return

        # Check node is online
        if node.status != NodeStatus.ONLINE:
            await websocket.send_json({
                "type": "error",
                "message": f"Node is {node.status.value}. Cannot connect to offline node."
            })
            await websocket.close(code=4004, reason="Node offline")
            return

        # Get terminal port from application_ports
        terminal_port = None
        if node.application_ports and "TERMINAL" in node.application_ports:
            terminal_port = node.application_ports["TERMINAL"].get("remote")

        if not terminal_port:
            await websocket.send_json({
                "type": "error",
                "message": "Terminal service not configured for this node"
            })
            await websocket.close(code=4005, reason="Terminal not configured")
            return

        # === Phase 3: Rate Limiting ===
        mgr = await get_session_manager()
        can_create, limit_msg = await mgr.can_create_session(user.id, node_id)
        if not can_create:
            await websocket.send_json({
                "type": "error",
                "message": limit_msg
            })
            await websocket.close(code=4029, reason="Rate limit exceeded")
            return

        # === Phase 4: Session Recording Setup ===
        client_ip = get_client_ip(websocket)
        user_agent = websocket.headers.get("user-agent")

        recorder = SessionRecorder(
            mongodb=mongodb_client.db,
            node_id=node_id,
            user_id=user.id,
            user_email=user.email,
            client_ip=client_ip,
            user_agent=user_agent,
        )
        await recorder.initialize()
        mgr.register_session(recorder)

        # Send session ID to client
        await websocket.send_json({
            "type": "session_id",
            "session_id": recorder.session_id
        })

        # === Phase 5: SSH Bridge ===
        # Get SSH credentials for the node
        # TODO: Store SSH credentials securely in the node configuration
        ssh_username = node.ssh_username if hasattr(node, 'ssh_username') and node.ssh_username else "lorenz"
        ssh_password = node.ssh_password if hasattr(node, 'ssh_password') and node.ssh_password else "profano.69"

        # Connect to node via reverse tunnel through SSH tunnel container
        # The SSH tunnel container exposes reverse tunnel ports from edge nodes
        ssh_tunnel_host = settings.SSH_TUNNEL_HOST if hasattr(settings, 'SSH_TUNNEL_HOST') else "ssh-tunnel"
        bridge = SSHBridge(
            websocket=websocket,
            host=ssh_tunnel_host,
            port=terminal_port,
            username=ssh_username,
            password=ssh_password,
            on_input=recorder.record_input,
            on_output=recorder.record_output,
        )

        try:
            # Try connecting with SSH
            connected = await bridge.connect()
            if not connected:
                await recorder.mark_error("SSH connection failed")
                mgr.unregister_session(recorder.session_id)
                await websocket.close(code=4006, reason="SSH connection failed")
                return

            # Send connected status
            await websocket.send_json({
                "type": "connected",
                "node_name": node.name,
                "node_id": node.id
            })

            logger.info(
                f"Terminal session started: "
                f"session={recorder.session_id}, "
                f"user={user.email}, "
                f"node={node.name}"
            )

            # Start bidirectional bridge
            await bridge.start()

        except WebSocketDisconnect:
            logger.info(f"Terminal WebSocket disconnected: session={recorder.session_id}")
        except Exception as e:
            logger.error(f"Terminal error: {e}")
            await recorder.mark_error(str(e))
        finally:
            # Cleanup
            await bridge.stop()
            await recorder.finalize()
            mgr.unregister_session(recorder.session_id)

            logger.info(
                f"Terminal session ended: "
                f"session={recorder.session_id}, "
                f"duration={recorder.total_input_bytes}b in, "
                f"{recorder.total_output_bytes}b out"
            )


@router.get("/sessions")
async def list_terminal_sessions(
    node_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    List terminal sessions for audit.
    Returns session metadata without full recording.
    """
    from app.terminal.session_recorder import get_session_history

    sessions = await get_session_history(
        mongodb=mongodb_client.db,
        node_id=node_id,
        limit=limit,
        offset=offset
    )

    # Convert ObjectId to string for JSON serialization
    for session in sessions:
        if "_id" in session:
            session["_id"] = str(session["_id"])

    return {
        "sessions": sessions,
        "limit": limit,
        "offset": offset
    }


@router.get("/sessions/{session_id}")
async def get_session_recording(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get full session recording for playback.
    Contains complete input/output with timestamps.
    """
    from app.terminal.session_recorder import get_session_recording as get_recording

    session = await get_recording(
        mongodb=mongodb_client.db,
        session_id=session_id
    )

    if not session:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Convert ObjectId to string
    if "_id" in session:
        session["_id"] = str(session["_id"])

    return session


@router.get("/active-count")
async def get_active_sessions_count():
    """Get count of currently active terminal sessions."""
    mgr = await get_session_manager()
    return {
        "active_sessions": mgr.get_active_count()
    }
