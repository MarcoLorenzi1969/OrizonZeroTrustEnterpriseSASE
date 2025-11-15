"""
Orizon Zero Trust Connect - VNC Session API Endpoints
For: Marco @ Syneto/Orizon

Remote Desktop via noVNC + WebSocket + Zero Trust
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Request,
    WebSocket,
    WebSocketDisconnect,
    Query,
)
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from loguru import logger
import jwt
from datetime import datetime

from app.core.database import get_db
from app.core.config import settings
from app.auth.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.vnc_session import VNCSessionStatus
from app.services.vnc_service import vnc_service
from app.schemas.vnc import (
    VNCSessionCreate,
    VNCSessionResponse,
    VNCSessionList,
    VNCSessionUpdate,
    VNCSessionStats,
    VNCSessionError,
)
from app.middleware.rate_limit import rate_limit


router = APIRouter()


# ============================================================================
# SESSION MANAGEMENT ENDPOINTS
# ============================================================================

@router.post(
    "/sessions",
    response_model=VNCSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create VNC session",
    description="""
    Create new VNC remote desktop session with Zero Trust validation.

    **Security Flow:**
    1. RBAC validation (User role or higher)
    2. Node ownership/access check
    3. Node status check (must be online)
    4. Rate limit check (max 5 sessions per user)
    5. ACL validation (if enabled)
    6. Dynamic port allocation
    7. JWT session token generation (exp ≤ 5 min)
    8. Agent tunnel creation command

    **Returns:**
    - `websocket_url`: Full WSS URL for noVNC client connection
    - `session_token`: JWT to authenticate WebSocket connection
    - `expires_at`: Session expiration timestamp
    - `tunnel_port`: Allocated port on hub
    """,
)
@rate_limit("10/minute")
async def create_vnc_session(
    session_data: VNCSessionCreate,
    request: Request,
    current_user: User = Depends(require_role(UserRole.USER)),
    db: AsyncSession = Depends(get_db),
):
    """
    Create new VNC session

    Requires: USER role or higher
    Rate limit: 10 requests/minute
    """
    try:
        # Get client info
        client_ip = request.client.host if request.client else "unknown"
        client_user_agent = request.headers.get("user-agent", "unknown")

        # Create session
        session = await vnc_service.create_session(
            db=db,
            user=current_user,
            session_data=session_data,
            client_ip=client_ip,
            client_user_agent=client_user_agent,
        )

        if not session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create VNC session. Check node status and rate limits.",
            )

        logger.info(
            f"✅ VNC session {session.id} created via API by {current_user.email}"
        )

        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating VNC session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {str(e)}",
        )


@router.get(
    "/sessions/{session_id}",
    response_model=VNCSessionResponse,
    summary="Get VNC session",
    description="Get VNC session details by ID. Users can only see their own sessions (except SuperUser).",
)
async def get_vnc_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get VNC session by ID"""
    session = await vnc_service.get_session(
        db=db, session_id=session_id, user=current_user
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"VNC session {session_id} not found",
        )

    return session


@router.get(
    "/sessions",
    response_model=VNCSessionList,
    summary="List VNC sessions",
    description="List VNC sessions with filtering and pagination.",
)
async def list_vnc_sessions(
    node_id: Optional[str] = Query(None, description="Filter by node ID"),
    status_filter: Optional[VNCSessionStatus] = Query(
        None, alias="status", description="Filter by session status"
    ),
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page (max 200)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List VNC sessions with filtering"""
    sessions = await vnc_service.list_sessions(
        db=db,
        user=current_user,
        node_id=node_id,
        status=status_filter,
        page=page,
        page_size=page_size,
    )

    return sessions


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Terminate VNC session",
    description="Terminate active VNC session. Closes tunnel and marks session as terminated.",
)
async def terminate_vnc_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Terminate VNC session"""
    success = await vnc_service.terminate_session(
        db=db, session_id=session_id, user=current_user
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"VNC session {session_id} not found or access denied",
        )

    logger.info(f"🛑 VNC session {session_id} terminated by {current_user.email}")
    return None


@router.patch(
    "/sessions/{session_id}",
    response_model=VNCSessionResponse,
    summary="Update VNC session",
    description="Update VNC session settings (limited fields: name, description, quality, etc.)",
)
async def update_vnc_session(
    session_id: str,
    update_data: VNCSessionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update VNC session (limited fields)"""
    # Get session
    session = await vnc_service.get_session(
        db=db, session_id=session_id, user=current_user
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"VNC session {session_id} not found",
        )

    # Update allowed fields
    from app.models.vnc_session import VNCSession, VNCQuality

    db_session = await db.get(VNCSession, session_id)

    if update_data.name:
        db_session.name = update_data.name
    if update_data.description is not None:
        db_session.description = update_data.description
    if update_data.quality:
        db_session.quality = VNCQuality(update_data.quality)
    if update_data.view_only is not None:
        db_session.view_only = update_data.view_only
    if update_data.tags is not None:
        db_session.tags = update_data.tags
    if update_data.metadata is not None:
        db_session.metadata = update_data.metadata

    await db.commit()
    await db.refresh(db_session)

    logger.info(f"✏️ VNC session {session_id} updated by {current_user.email}")

    return VNCSessionResponse.model_validate(db_session)


@router.get(
    "/stats",
    response_model=VNCSessionStats,
    summary="Get VNC statistics",
    description="Get VNC session statistics (total, active, bytes transferred, etc.)",
)
async def get_vnc_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get VNC session statistics"""
    stats = await vnc_service.get_session_stats(db=db, user=current_user)
    return stats


# ============================================================================
# WEBSOCKET ENDPOINT (for VNC Gateway proxy)
# ============================================================================

@router.websocket("/ws/{session_id}")
async def vnc_websocket(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(..., description="JWT session token"),
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket endpoint for VNC connection

    This endpoint is used by the VNC Gateway to validate tokens.
    The actual VNC traffic is handled by the VNC Gateway service (websockify).

    Flow:
    1. Client connects to this WebSocket with session_id and JWT token
    2. Backend validates token
    3. Backend returns session info to VNC Gateway
    4. VNC Gateway proxies RFB traffic to tunnel port

    **Note:** This is a metadata/validation endpoint.
    The actual VNC proxy is handled by the separate VNC Gateway service.
    """
    await websocket.accept()

    try:
        # Validate JWT token
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            await websocket.send_json(
                {"error": "TOKEN_EXPIRED", "message": "Session token has expired"}
            )
            await websocket.close(code=4001)
            return
        except jwt.InvalidTokenError as e:
            await websocket.send_json(
                {"error": "INVALID_TOKEN", "message": f"Invalid token: {str(e)}"}
            )
            await websocket.close(code=4002)
            return

        # Verify session_id matches
        if payload.get("session_id") != session_id:
            await websocket.send_json(
                {
                    "error": "SESSION_MISMATCH",
                    "message": "Session ID does not match token",
                }
            )
            await websocket.close(code=4003)
            return

        # Get session from database
        from app.models.vnc_session import VNCSession

        db_session = await db.get(VNCSession, session_id)

        if not db_session:
            await websocket.send_json(
                {"error": "SESSION_NOT_FOUND", "message": "VNC session not found"}
            )
            await websocket.close(code=4004)
            return

        # Check session is not expired
        if db_session.is_expired:
            db_session.status = VNCSessionStatus.EXPIRED
            await db.commit()
            await websocket.send_json(
                {"error": "SESSION_EXPIRED", "message": "VNC session has expired"}
            )
            await websocket.close(code=4005)
            return

        # Update session status
        if db_session.status == VNCSessionStatus.CONNECTING:
            db_session.status = VNCSessionStatus.ACTIVE
            db_session.started_at = datetime.utcnow()
            await db.commit()

        # Send connection info to VNC Gateway
        await websocket.send_json(
            {
                "status": "AUTHORIZED",
                "session_id": session_id,
                "tunnel_port": db_session.tunnel_port,
                "vnc_host": db_session.vnc_host,
                "vnc_port": db_session.vnc_port,
                "quality": db_session.quality.value,
                "view_only": db_session.view_only,
            }
        )

        logger.info(f"✅ VNC WebSocket authorized for session {session_id}")

        # Keep connection alive for metrics updates
        while True:
            try:
                # Receive metrics from VNC Gateway
                data = await websocket.receive_json()

                if data.get("type") == "metrics":
                    # Update session metrics
                    db_session.bytes_sent = data.get("bytes_sent", db_session.bytes_sent)
                    db_session.bytes_received = data.get("bytes_received", db_session.bytes_received)
                    db_session.frames_sent = data.get("frames_sent", db_session.frames_sent)
                    db_session.latency_ms = data.get("latency_ms")
                    db_session.last_activity_at = datetime.utcnow()
                    await db.commit()

                elif data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        logger.info(f"🔌 VNC WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"❌ VNC WebSocket error: {e}")
        await websocket.send_json(
            {"error": "INTERNAL_ERROR", "message": str(e)}
        )
    finally:
        # Update session status on disconnect
        try:
            from app.models.vnc_session import VNCSession

            db_session = await db.get(VNCSession, session_id)
            if db_session and db_session.status == VNCSessionStatus.ACTIVE:
                db_session.status = VNCSessionStatus.DISCONNECTED
                db_session.ended_at = datetime.utcnow()
                await db.commit()
                logger.info(f"🔌 VNC session {session_id} marked as disconnected")
        except Exception as e:
            logger.error(f"❌ Error updating session status: {e}")

        try:
            await websocket.close()
        except:
            pass
