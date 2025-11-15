"""
Orizon Zero Trust Connect - VNC Session Service
For: Marco @ Syneto/Orizon

Complete VNC Remote Desktop session management with Zero Trust
"""

import asyncio
import uuid
import jwt
import random
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from loguru import logger

from app.models.vnc_session import VNCSession, VNCSessionStatus, VNCQuality
from app.models.node import Node, NodeStatus
from app.models.user import User, UserRole
from app.models.tunnel import Tunnel, TunnelStatus, TunnelType
from app.schemas.vnc import (
    VNCSessionCreate,
    VNCSessionResponse,
    VNCSessionList,
    VNCSessionStats,
)
from app.core.redis import redis_client
from app.core.config import settings
from app.core.mongodb import get_mongodb
from app.services.acl_service import ACLService


class VNCService:
    """
    Complete VNC session management service

    Zero Trust Architecture:
    1. RBAC validation (SuperUser/SuperAdmin/Admin/User)
    2. ACL validation (Zero Trust rules)
    3. Node status check (must be online)
    4. Dynamic port allocation (VNC Gateway ports)
    5. JWT session token generation (exp ≤ 5 min)
    6. Agent tunnel creation command
    7. Full audit logging

    Flow:
    Client → Create Session API → VNC Service → Agent (WebSocket) → Tunnel Creation
    Client → WebSocket → VNC Gateway → Tunnel (TCP) → Edge Agent → VNC Server
    """

    # Port allocation
    VNC_PORT_MIN = 40000  # VNC Gateway port range
    VNC_PORT_MAX = 49999
    TUNNEL_PORT_MIN = 50000  # Edge tunnel port range
    TUNNEL_PORT_MAX = 59999

    # Session settings
    MAX_SESSION_DURATION = 3600  # 1 hour max
    DEFAULT_SESSION_DURATION = 300  # 5 minutes default
    SESSION_CLEANUP_INTERVAL = 60  # Check expired sessions every 60s

    # Rate limiting
    MAX_SESSIONS_PER_USER = 5
    MAX_SESSIONS_PER_NODE = 3
    RATE_LIMIT_WINDOW = 3600  # 1 hour

    def __init__(self):
        """Initialize VNC service"""
        self._port_locks: Dict[int, asyncio.Lock] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self.acl_service = ACLService()

    async def start_cleanup_task(self):
        """Start background task to cleanup expired sessions"""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._cleanup_expired_sessions())
            logger.info("✅ VNC session cleanup task started")

    async def stop_cleanup_task(self):
        """Stop cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("🛑 VNC session cleanup task stopped")

    # ========================================================================
    # SESSION CREATION
    # ========================================================================

    async def create_session(
        self,
        db: AsyncSession,
        user: User,
        session_data: VNCSessionCreate,
        client_ip: str,
        client_user_agent: str,
    ) -> Optional[VNCSessionResponse]:
        """
        Create new VNC session with Zero Trust validation

        Steps:
        1. Validate RBAC (user has access to node)
        2. Validate node status (must be online)
        3. Check rate limits
        4. Validate ACL rules
        5. Allocate ports (tunnel + VNC gateway)
        6. Create session in DB
        7. Generate JWT token
        8. Send tunnel creation command to agent
        9. Log audit event

        Returns:
            VNCSessionResponse with WebSocket URL and token
        """
        try:
            # 1. Get node and validate ownership/access
            node = await self._get_and_validate_node(db, user, session_data.node_id)
            if not node:
                logger.warning(f"⚠️ Node {session_data.node_id} not found or access denied for user {user.id}")
                return None

            # 2. Validate node is online
            if node.status != NodeStatus.ONLINE:
                logger.warning(f"⚠️ Node {node.name} is {node.status}, cannot create VNC session")
                await self._log_event(
                    user.id,
                    session_data.node_id,
                    "vnc_session_creation_failed",
                    {"reason": f"node_status_{node.status}"},
                )
                return None

            # 3. Check rate limits
            if not await self._check_rate_limits(db, user.id, session_data.node_id):
                logger.warning(f"⚠️ Rate limit exceeded for user {user.id}")
                return None

            # 4. Validate ACL (if required)
            if session_data.require_acl_validation:
                if not await self._validate_acl(db, user, node, client_ip):
                    logger.warning(f"⚠️ ACL validation failed for user {user.id} → node {node.id}")
                    await self._log_event(
                        user.id,
                        node.id,
                        "vnc_session_acl_denied",
                        {"client_ip": client_ip},
                    )
                    return None

            # 5. Allocate ports
            tunnel_port = await self._allocate_port(self.TUNNEL_PORT_MIN, self.TUNNEL_PORT_MAX)
            if not tunnel_port:
                logger.error("❌ Failed to allocate tunnel port")
                return None

            # 6. Create session in database
            session_id = str(uuid.uuid4())
            expires_at = datetime.utcnow() + timedelta(seconds=session_data.max_duration_seconds)

            vnc_session = VNCSession(
                id=session_id,
                name=session_data.name,
                description=session_data.description,
                status=VNCSessionStatus.PENDING,
                # Connection
                tunnel_port=tunnel_port,
                websocket_path=f"/api/v1/vnc/ws/{session_id}",
                # VNC config
                vnc_host=session_data.vnc_host,
                vnc_port=session_data.vnc_port,
                quality=VNCQuality(session_data.quality),
                # Display
                screen_width=session_data.screen_width,
                screen_height=session_data.screen_height,
                allow_resize=session_data.allow_resize,
                # Security
                view_only=session_data.view_only,
                require_acl_validation=session_data.require_acl_validation,
                # Timing
                max_duration_seconds=session_data.max_duration_seconds,
                expires_at=expires_at,
                # Client
                client_ip=client_ip,
                client_user_agent=client_user_agent,
                # Relationships
                node_id=node.id,
                user_id=user.id,
                # Metadata
                tags=session_data.tags,
                metadata=session_data.metadata,
            )

            db.add(vnc_session)
            await db.commit()
            await db.refresh(vnc_session)

            # 7. Generate JWT session token
            session_token = self._generate_session_token(
                session_id=session_id,
                user_id=user.id,
                node_id=node.id,
                tunnel_port=tunnel_port,
                expires_at=expires_at,
            )

            vnc_session.session_token = session_token
            await db.commit()

            # 8. Send tunnel creation command to agent via WebSocket
            tunnel_created = await self._request_agent_tunnel(
                node_id=node.id,
                session_id=session_id,
                tunnel_port=tunnel_port,
                vnc_host=session_data.vnc_host,
                vnc_port=session_data.vnc_port,
            )

            if not tunnel_created:
                # Rollback session
                vnc_session.status = VNCSessionStatus.ERROR
                vnc_session.last_error = "Failed to create tunnel on edge agent"
                await db.commit()
                logger.error(f"❌ Agent tunnel creation failed for session {session_id}")
                return None

            # Update status to CONNECTING
            vnc_session.status = VNCSessionStatus.CONNECTING
            await db.commit()

            # 9. Log success
            await self._log_event(
                user.id,
                node.id,
                "vnc_session_created",
                {
                    "session_id": session_id,
                    "tunnel_port": tunnel_port,
                    "quality": session_data.quality,
                    "duration": session_data.max_duration_seconds,
                },
            )

            logger.info(f"✅ VNC session {session_id} created for {user.email} → {node.name}")

            # Return response
            return VNCSessionResponse.model_validate(vnc_session)

        except Exception as e:
            logger.error(f"❌ Failed to create VNC session: {e}")
            await db.rollback()
            return None

    # ========================================================================
    # SESSION MANAGEMENT
    # ========================================================================

    async def get_session(
        self, db: AsyncSession, session_id: str, user: User
    ) -> Optional[VNCSessionResponse]:
        """Get VNC session by ID (with ownership check)"""
        stmt = select(VNCSession).where(VNCSession.id == session_id)

        # Non-SuperUser can only see their own sessions
        if user.role != UserRole.SUPERUSER:
            stmt = stmt.where(VNCSession.user_id == user.id)

        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        if not session:
            return None

        return VNCSessionResponse.model_validate(session)

    async def list_sessions(
        self,
        db: AsyncSession,
        user: User,
        node_id: Optional[str] = None,
        status: Optional[VNCSessionStatus] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> VNCSessionList:
        """List VNC sessions with filtering and pagination"""
        stmt = select(VNCSession)

        # RBAC filtering
        if user.role != UserRole.SUPERUSER:
            stmt = stmt.where(VNCSession.user_id == user.id)

        # Filters
        if node_id:
            stmt = stmt.where(VNCSession.node_id == node_id)
        if status:
            stmt = stmt.where(VNCSession.status == status)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar()

        # Pagination
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size).order_by(VNCSession.created_at.desc())

        result = await db.execute(stmt)
        sessions = result.scalars().all()

        return VNCSessionList(
            total=total,
            sessions=[VNCSessionResponse.model_validate(s) for s in sessions],
            page=page,
            page_size=page_size,
        )

    async def terminate_session(
        self, db: AsyncSession, session_id: str, user: User
    ) -> bool:
        """Terminate VNC session"""
        session = await db.get(VNCSession, session_id)
        if not session:
            return False

        # Check ownership (non-SuperUser can only terminate their own)
        if user.role != UserRole.SUPERUSER and session.user_id != user.id:
            logger.warning(f"⚠️ User {user.id} tried to terminate session {session_id} they don't own")
            return False

        # Send termination command to agent
        await self._request_agent_tunnel_close(session.node_id, session_id)

        # Update session
        session.status = VNCSessionStatus.TERMINATED
        session.ended_at = datetime.utcnow()
        await db.commit()

        # Log event
        await self._log_event(
            user.id,
            session.node_id,
            "vnc_session_terminated",
            {"session_id": session_id},
        )

        logger.info(f"🛑 VNC session {session_id} terminated by {user.email}")
        return True

    async def get_session_stats(self, db: AsyncSession, user: User) -> VNCSessionStats:
        """Get VNC session statistics"""
        stmt = select(VNCSession)

        # RBAC filtering
        if user.role != UserRole.SUPERUSER:
            stmt = stmt.where(VNCSession.user_id == user.id)

        result = await db.execute(stmt)
        sessions = result.scalars().all()

        total_sessions = len(sessions)
        active_sessions = len([s for s in sessions if s.status == VNCSessionStatus.ACTIVE])
        total_bytes_sent = sum(s.bytes_sent for s in sessions)
        total_bytes_received = sum(s.bytes_received for s in sessions)
        total_frames_sent = sum(s.frames_sent for s in sessions)

        # Average latency for active sessions
        active_latencies = [s.latency_ms for s in sessions if s.status == VNCSessionStatus.ACTIVE and s.latency_ms]
        avg_latency_ms = sum(active_latencies) / len(active_latencies) if active_latencies else None

        # Count by status
        sessions_by_status = {}
        for status in VNCSessionStatus:
            count = len([s for s in sessions if s.status == status])
            if count > 0:
                sessions_by_status[status.value] = count

        return VNCSessionStats(
            total_sessions=total_sessions,
            active_sessions=active_sessions,
            total_bytes_sent=total_bytes_sent,
            total_bytes_received=total_bytes_received,
            total_frames_sent=total_frames_sent,
            avg_latency_ms=avg_latency_ms,
            sessions_by_status=sessions_by_status,
        )

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    async def _get_and_validate_node(
        self, db: AsyncSession, user: User, node_id: str
    ) -> Optional[Node]:
        """Get node and validate user has access"""
        node = await db.get(Node, node_id)
        if not node:
            return None

        # SuperUser can access all nodes
        if user.role == UserRole.SUPERUSER:
            return node

        # Others can only access their own nodes
        if node.owner_id != user.id:
            return None

        return node

    async def _check_rate_limits(
        self, db: AsyncSession, user_id: str, node_id: str
    ) -> bool:
        """Check rate limits for session creation"""
        # Check user limit
        user_stmt = select(func.count()).select_from(VNCSession).where(
            and_(
                VNCSession.user_id == user_id,
                VNCSession.status.in_([VNCSessionStatus.ACTIVE, VNCSessionStatus.CONNECTING]),
            )
        )
        user_result = await db.execute(user_stmt)
        user_active = user_result.scalar()

        if user_active >= self.MAX_SESSIONS_PER_USER:
            logger.warning(f"⚠️ User {user_id} has {user_active} active sessions (max {self.MAX_SESSIONS_PER_USER})")
            return False

        # Check node limit
        node_stmt = select(func.count()).select_from(VNCSession).where(
            and_(
                VNCSession.node_id == node_id,
                VNCSession.status.in_([VNCSessionStatus.ACTIVE, VNCSessionStatus.CONNECTING]),
            )
        )
        node_result = await db.execute(node_stmt)
        node_active = node_result.scalar()

        if node_active >= self.MAX_SESSIONS_PER_NODE:
            logger.warning(f"⚠️ Node {node_id} has {node_active} active sessions (max {self.MAX_SESSIONS_PER_NODE})")
            return False

        return True

    async def _validate_acl(
        self, db: AsyncSession, user: User, node: Node, client_ip: str
    ) -> bool:
        """Validate ACL rules (Zero Trust)"""
        # Use existing ACL service
        decision = await self.acl_service.evaluate_access(
            db=db,
            source_ip=client_ip,
            destination_ip=node.ip_address,
            protocol="tcp",
            port=5900,  # VNC port
            user_id=user.id,
        )
        return decision.action == "ALLOW"

    async def _allocate_port(self, min_port: int, max_port: int) -> Optional[int]:
        """Allocate available port with Redis locking"""
        for attempt in range(20):  # Try 20 random ports
            port = random.randint(min_port, max_port)
            key = f"vnc:port:{port}"

            # Try to acquire lock in Redis
            if await redis_client.set(key, "1", ex=7200, nx=True):  # 2 hour lock
                logger.debug(f"✅ Allocated port {port}")
                return port

        logger.error(f"❌ Failed to allocate port after 20 attempts")
        return None

    def _generate_session_token(
        self,
        session_id: str,
        user_id: str,
        node_id: str,
        tunnel_port: int,
        expires_at: datetime,
    ) -> str:
        """
        Generate JWT session token

        Payload:
        - session_id: VNC session UUID
        - user_id: User UUID
        - node_id: Node UUID
        - tunnel_port: Allocated tunnel port
        - exp: Expiration timestamp
        """
        payload = {
            "session_id": session_id,
            "user_id": user_id,
            "node_id": node_id,
            "tunnel_port": tunnel_port,
            "exp": int(expires_at.timestamp()),
            "iat": int(datetime.utcnow().timestamp()),
        }

        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        return token

    async def _request_agent_tunnel(
        self,
        node_id: str,
        session_id: str,
        tunnel_port: int,
        vnc_host: str,
        vnc_port: int,
    ) -> bool:
        """
        Send tunnel creation request to edge agent via WebSocket

        Message format:
        {
            "action": "create_vnc_tunnel",
            "session_id": "uuid",
            "tunnel_port": 50000,
            "vnc_host": "localhost",
            "vnc_port": 5900
        }
        """
        try:
            # Get WebSocket manager
            from app.websocket.manager import websocket_manager

            message = {
                "action": "create_vnc_tunnel",
                "session_id": session_id,
                "tunnel_port": tunnel_port,
                "vnc_host": vnc_host,
                "vnc_port": vnc_port,
            }

            # Send to agent
            await websocket_manager.send_to_node(node_id, message)

            # TODO: Wait for agent confirmation (implement ack mechanism)
            # For now, assume success
            logger.info(f"📤 Sent VNC tunnel creation request to node {node_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to send tunnel request to agent: {e}")
            return False

    async def _request_agent_tunnel_close(self, node_id: str, session_id: str) -> bool:
        """Send tunnel close request to agent"""
        try:
            from app.websocket.manager import websocket_manager

            message = {
                "action": "close_vnc_tunnel",
                "session_id": session_id,
            }

            await websocket_manager.send_to_node(node_id, message)
            logger.info(f"📤 Sent VNC tunnel close request to node {node_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to send tunnel close request: {e}")
            return False

    async def _log_event(
        self, user_id: str, node_id: str, event_type: str, details: dict
    ):
        """Log audit event to MongoDB"""
        try:
            mongodb = await get_mongodb()
            await mongodb.audit_logs.insert_one(
                {
                    "timestamp": datetime.utcnow(),
                    "user_id": user_id,
                    "node_id": node_id,
                    "event_type": event_type,
                    "details": details,
                    "service": "vnc",
                }
            )
        except Exception as e:
            logger.error(f"❌ Failed to log audit event: {e}")

    async def _cleanup_expired_sessions(self):
        """Background task to cleanup expired sessions"""
        logger.info("🧹 Starting VNC session cleanup task")

        while True:
            try:
                await asyncio.sleep(self.SESSION_CLEANUP_INTERVAL)

                # Get database session
                from app.core.database import AsyncSessionLocal

                async with AsyncSessionLocal() as db:
                    # Find expired sessions
                    stmt = select(VNCSession).where(
                        and_(
                            VNCSession.expires_at < datetime.utcnow(),
                            VNCSession.status.in_(
                                [
                                    VNCSessionStatus.PENDING,
                                    VNCSessionStatus.CONNECTING,
                                    VNCSessionStatus.ACTIVE,
                                ]
                            ),
                        )
                    )

                    result = await db.execute(stmt)
                    expired_sessions = result.scalars().all()

                    for session in expired_sessions:
                        logger.info(f"🧹 Cleaning up expired session {session.id}")

                        # Close tunnel
                        await self._request_agent_tunnel_close(session.node_id, session.id)

                        # Update status
                        session.status = VNCSessionStatus.EXPIRED
                        session.ended_at = datetime.utcnow()

                    if expired_sessions:
                        await db.commit()
                        logger.info(f"🧹 Cleaned up {len(expired_sessions)} expired sessions")

            except asyncio.CancelledError:
                logger.info("🛑 VNC cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Error in cleanup task: {e}")


# Global instance
vnc_service = VNCService()
