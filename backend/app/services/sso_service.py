"""
Orizon Zero Trust - SSO Session Manager
Gestione centralizzata delle sessioni Single Sign-On
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import json
import hashlib

from app.models.user import User
from app.core.redis import get_redis
from app.auth.security import create_access_token, create_refresh_token
from app.schemas import Token


class SSOSessionManager:
    """Gestione sessioni SSO centralizzata con Redis"""

    SESSION_PREFIX = "sso:session:"
    USER_SESSIONS_PREFIX = "sso:user_sessions:"
    DEVICE_PREFIX = "sso:device:"

    @staticmethod
    def _generate_session_id(user_id: str, device_info: str) -> str:
        """Genera ID sessione univoco"""
        timestamp = datetime.utcnow().isoformat()
        data = f"{user_id}:{device_info}:{timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()

    @staticmethod
    async def create_session(
        user: User,
        device_info: Dict,
        ip_address: str
    ) -> Dict:
        """Crea nuova sessione SSO"""
        redis_client = await get_redis()
        redis = redis_client.redis  # Access underlying Redis

        # Genera token JWT
        access_token = create_access_token(
            data={"sub": user.id, "email": user.email, "role": user.role}
        )
        refresh_token = create_refresh_token(
            data={"sub": user.id, "email": user.email, "role": user.role}
        )

        # Genera session ID
        device_fingerprint = device_info.get("user_agent", "") + ip_address
        session_id = SSOSessionManager._generate_session_id(user.id, device_fingerprint)

        # Dati sessione
        session_data = {
            "session_id": session_id,
            "user_id": user.id,
            "email": user.email,
            "role": user.role,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "device_info": device_info,
            "ip_address": ip_address,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "is_active": True
        }

        # Salva sessione in Redis (TTL 7 giorni)
        session_key = f"{SSOSessionManager.SESSION_PREFIX}{session_id}"
        await redis_client.set(
            session_key,
            session_data,
            expire=60 * 60 * 24 * 7  # 7 giorni
        )

        # Aggiungi alla lista sessioni utente
        user_sessions_key = f"{SSOSessionManager.USER_SESSIONS_PREFIX}{user.id}"
        await redis.sadd(user_sessions_key, session_id)
        await redis.expire(user_sessions_key, 60 * 60 * 24 * 7)

        return {
            "session_id": session_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 60 * 60 * 24  # 24 ore
        }

    @staticmethod
    async def get_session(session_id: str) -> Optional[Dict]:
        """Recupera sessione da session ID"""
        redis_client = await get_redis()
        session_key = f"{SSOSessionManager.SESSION_PREFIX}{session_id}"

        session_data = await redis_client.get(session_key)
        if session_data:
            return json.loads(session_data)
        return None

    @staticmethod
    async def update_activity(session_id: str):
        """Aggiorna last_activity della sessione"""
        redis_client = await get_redis()
        session = await SSOSessionManager.get_session(session_id)

        if session:
            session["last_activity"] = datetime.utcnow().isoformat()
            session_key = f"{SSOSessionManager.SESSION_PREFIX}{session_id}"
            await redis_client.set(
                session_key,
                session,
                expire=60 * 60 * 24 * 7
            )

    @staticmethod
    async def get_user_sessions(user_id: str) -> List[Dict]:
        """Recupera tutte le sessioni attive di un utente"""
        redis_client = await get_redis()
        redis = redis_client.redis
        user_sessions_key = f"{SSOSessionManager.USER_SESSIONS_PREFIX}{user_id}"

        session_ids = await redis.smembers(user_sessions_key)
        sessions = []

        for session_id in session_ids:
            session = await SSOSessionManager.get_session(session_id)
            if session and session.get("is_active"):
                sessions.append(session)

        return sessions

    @staticmethod
    async def revoke_session(session_id: str):
        """Revoca una sessione specifica"""
        redis_client = await get_redis()
        redis = redis_client.redis
        session_key = f"{SSOSessionManager.SESSION_PREFIX}{session_id}"

        session = await SSOSessionManager.get_session(session_id)
        if session:
            # Rimuovi dalla lista utente
            user_sessions_key = f"{SSOSessionManager.USER_SESSIONS_PREFIX}{session['user_id']}"
            await redis.srem(user_sessions_key, session_id)

            # Elimina sessione
            await redis_client.delete(session_key)

    @staticmethod
    async def revoke_all_user_sessions(user_id: str):
        """Revoca tutte le sessioni di un utente (logout globale)"""
        sessions = await SSOSessionManager.get_user_sessions(user_id)

        for session in sessions:
            await SSOSessionManager.revoke_session(session["session_id"])

    @staticmethod
    async def validate_sso_token(access_token: str) -> Optional[Dict]:
        """Valida token SSO e ritorna info utente"""
        redis = await get_redis()

        # Cerca sessione con questo token
        # In produzione usare un indice token->session
        # Per ora iteriamo (ottimizzare in futuro)
        return None  # Implementare lookup ottimizzato
