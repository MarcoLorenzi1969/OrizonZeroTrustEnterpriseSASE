"""
Orizon Zero Trust - SSO Session Manager
Manages user sessions across devices with Redis storage
"""
import uuid
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token
from app.models.user import User

# Try to import Redis, fallback to in-memory storage if not available
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class SSOSessionManager:
    """
    Manages SSO sessions with Redis storage
    Falls back to in-memory storage if Redis is unavailable
    """

    # In-memory fallback storage
    _sessions: Dict[str, Dict] = {}
    _user_sessions: Dict[str, List[str]] = {}
    _redis_client: Optional[Any] = None

    @classmethod
    async def _get_redis(cls) -> Optional[Any]:
        """Get Redis client, create if needed"""
        if not REDIS_AVAILABLE:
            return None

        if cls._redis_client is None:
            try:
                cls._redis_client = redis.Redis(
                    host=getattr(settings, 'REDIS_HOST', 'localhost'),
                    port=getattr(settings, 'REDIS_PORT', 6379),
                    db=getattr(settings, 'REDIS_DB', 0),
                    decode_responses=True
                )
                await cls._redis_client.ping()
            except Exception:
                cls._redis_client = None

        return cls._redis_client

    @classmethod
    async def create_session(
        cls,
        user: User,
        device_info: Dict[str, str],
        ip_address: str
    ) -> Dict[str, Any]:
        """
        Create a new SSO session for a user

        Args:
            user: User model instance
            device_info: Dictionary with device information
            ip_address: Client IP address

        Returns:
            Dictionary with tokens and session info
        """
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()

        # Create tokens
        access_token_expires = timedelta(minutes=getattr(settings, 'ACCESS_TOKEN_EXPIRE_MINUTES', 60))
        access_token = create_access_token(
            subject=str(user.id),
            role=user.role,
            scopes=[],
            expires_delta=access_token_expires
        )

        refresh_token = create_refresh_token(
            subject=str(user.id)
        )

        # Session data
        session_data = {
            "session_id": session_id,
            "user_id": str(user.id),
            "device_info": device_info,
            "ip_address": ip_address,
            "created_at": now.isoformat(),
            "last_activity": now.isoformat(),
            "is_active": True,
            "access_token": access_token,
            "refresh_token": refresh_token
        }

        # Store session
        redis_client = await cls._get_redis()
        if redis_client:
            try:
                # Store session with 7-day TTL
                await redis_client.setex(
                    f"sso:session:{session_id}",
                    timedelta(days=7),
                    json.dumps(session_data)
                )
                # Add to user's session list
                await redis_client.sadd(f"sso:user:{user.id}", session_id)
            except Exception:
                # Fallback to in-memory
                cls._sessions[session_id] = session_data
                if str(user.id) not in cls._user_sessions:
                    cls._user_sessions[str(user.id)] = []
                cls._user_sessions[str(user.id)].append(session_id)
        else:
            # In-memory storage
            cls._sessions[session_id] = session_data
            if str(user.id) not in cls._user_sessions:
                cls._user_sessions[str(user.id)] = []
            cls._user_sessions[str(user.id)].append(session_id)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": int(access_token_expires.total_seconds()),
            "session_id": session_id
        }

    @classmethod
    async def get_session(cls, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID"""
        redis_client = await cls._get_redis()

        if redis_client:
            try:
                data = await redis_client.get(f"sso:session:{session_id}")
                if data:
                    return json.loads(data)
            except Exception:
                pass

        # Fallback to in-memory
        return cls._sessions.get(session_id)

    @classmethod
    async def get_user_sessions(cls, user_id: str) -> List[Dict[str, Any]]:
        """Get all active sessions for a user"""
        sessions = []
        redis_client = await cls._get_redis()

        if redis_client:
            try:
                session_ids = await redis_client.smembers(f"sso:user:{user_id}")
                for sid in session_ids:
                    session = await cls.get_session(sid)
                    if session and session.get("is_active"):
                        # Don't return tokens in list
                        safe_session = {k: v for k, v in session.items()
                                       if k not in ["access_token", "refresh_token"]}
                        sessions.append(safe_session)
            except Exception:
                pass
        else:
            # In-memory fallback
            user_session_ids = cls._user_sessions.get(str(user_id), [])
            for sid in user_session_ids:
                session = cls._sessions.get(sid)
                if session and session.get("is_active"):
                    safe_session = {k: v for k, v in session.items()
                                   if k not in ["access_token", "refresh_token"]}
                    sessions.append(safe_session)

        return sessions

    @classmethod
    async def revoke_session(cls, session_id: str) -> bool:
        """Revoke a specific session"""
        redis_client = await cls._get_redis()

        if redis_client:
            try:
                session_data = await redis_client.get(f"sso:session:{session_id}")
                if session_data:
                    session = json.loads(session_data)
                    session["is_active"] = False
                    await redis_client.setex(
                        f"sso:session:{session_id}",
                        timedelta(days=1),  # Keep for audit
                        json.dumps(session)
                    )
                    return True
            except Exception:
                pass

        # In-memory fallback
        if session_id in cls._sessions:
            cls._sessions[session_id]["is_active"] = False
            return True

        return False

    @classmethod
    async def revoke_all_user_sessions(cls, user_id: str) -> int:
        """Revoke all sessions for a user"""
        count = 0
        redis_client = await cls._get_redis()

        if redis_client:
            try:
                session_ids = await redis_client.smembers(f"sso:user:{user_id}")
                for sid in session_ids:
                    if await cls.revoke_session(sid):
                        count += 1
            except Exception:
                pass
        else:
            # In-memory fallback
            user_session_ids = cls._user_sessions.get(str(user_id), [])
            for sid in user_session_ids:
                if sid in cls._sessions:
                    cls._sessions[sid]["is_active"] = False
                    count += 1

        return count

    @classmethod
    async def update_activity(cls, session_id: str) -> bool:
        """Update last activity timestamp for a session"""
        redis_client = await cls._get_redis()
        now = datetime.utcnow().isoformat()

        if redis_client:
            try:
                session_data = await redis_client.get(f"sso:session:{session_id}")
                if session_data:
                    session = json.loads(session_data)
                    session["last_activity"] = now
                    await redis_client.setex(
                        f"sso:session:{session_id}",
                        timedelta(days=7),
                        json.dumps(session)
                    )
                    return True
            except Exception:
                pass

        # In-memory fallback
        if session_id in cls._sessions:
            cls._sessions[session_id]["last_activity"] = now
            return True

        return False
