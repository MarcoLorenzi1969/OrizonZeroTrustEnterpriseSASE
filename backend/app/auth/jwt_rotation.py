"""
Orizon Zero Trust Connect - JWT Secret Rotation
For: Marco @ Syneto/Orizon

Automatic JWT secret rotation for enhanced security
Features:
- Automatic secret rotation every 30 days
- Grace period for old secrets (7 days)
- Redis-based secret storage
- Seamless token validation during rotation
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from jose import JWTError, jwt
from loguru import logger

from app.core.redis import redis_client
from app.core.config import settings


class JWTRotationManager:
    """
    JWT Secret Rotation Manager

    Features:
    - Automatic secret rotation every 30 days
    - Multiple active secrets (current + previous) for grace period
    - Redis storage for distributed systems
    - Background rotation task
    """

    # Rotation settings
    ROTATION_INTERVAL_DAYS = 30  # Rotate every 30 days
    GRACE_PERIOD_DAYS = 7  # Keep old secret for 7 days
    SECRET_LENGTH = 64  # 512 bits

    # Redis keys
    CURRENT_SECRET_KEY = "jwt:secret:current"
    PREVIOUS_SECRET_KEY = "jwt:secret:previous"
    ROTATION_DATE_KEY = "jwt:secret:rotation_date"
    NEXT_ROTATION_KEY = "jwt:secret:next_rotation"

    @classmethod
    async def initialize(cls):
        """
        Initialize JWT secret rotation system

        Creates initial secret if none exists
        """
        try:
            # Check if current secret exists
            current_secret = await redis_client.get(cls.CURRENT_SECRET_KEY)

            if not current_secret:
                logger.info("🔐 No JWT secret found, generating initial secret...")
                await cls.rotate_secret(is_initial=True)
            else:
                logger.info("🔐 JWT rotation manager initialized")

                # Check if rotation is needed
                await cls.check_and_rotate()

        except Exception as e:
            logger.error(f"❌ Failed to initialize JWT rotation: {e}")
            raise

    @classmethod
    async def rotate_secret(cls, is_initial: bool = False) -> bool:
        """
        Rotate JWT secret

        Args:
            is_initial: True if this is the initial secret generation

        Returns:
            True if rotation successful, False otherwise
        """
        try:
            # Get current secret (if exists)
            current_secret = await redis_client.get(cls.CURRENT_SECRET_KEY)

            # Generate new secret
            new_secret = secrets.token_urlsafe(cls.SECRET_LENGTH)

            # Save old secret as previous (for grace period)
            if current_secret and not is_initial:
                await redis_client.set_with_expiry(
                    cls.PREVIOUS_SECRET_KEY,
                    current_secret,
                    expiry=cls.GRACE_PERIOD_DAYS * 86400  # 7 days
                )
                logger.info("🔄 Old JWT secret moved to previous (7-day grace period)")

            # Set new secret as current
            await redis_client.set(cls.CURRENT_SECRET_KEY, new_secret)

            # Update rotation metadata
            now = datetime.utcnow()
            next_rotation = now + timedelta(days=cls.ROTATION_INTERVAL_DAYS)

            await redis_client.set(
                cls.ROTATION_DATE_KEY,
                now.isoformat()
            )

            await redis_client.set(
                cls.NEXT_ROTATION_KEY,
                next_rotation.isoformat()
            )

            if is_initial:
                logger.info("✅ Initial JWT secret generated successfully")
            else:
                logger.info(
                    f"✅ JWT secret rotated successfully "
                    f"(next rotation: {next_rotation.strftime('%Y-%m-%d %H:%M:%S')})"
                )

            # Log to audit
            await cls._log_rotation_event(is_initial)

            return True

        except Exception as e:
            logger.error(f"❌ Failed to rotate JWT secret: {e}")
            return False

    @classmethod
    async def get_current_secret(cls) -> Optional[str]:
        """
        Get current JWT secret

        Returns:
            Current secret or None if not found
        """
        try:
            secret = await redis_client.get(cls.CURRENT_SECRET_KEY)

            if not secret:
                logger.warning("⚠️ No current JWT secret found, initializing...")
                await cls.initialize()
                secret = await redis_client.get(cls.CURRENT_SECRET_KEY)

            return secret

        except Exception as e:
            logger.error(f"❌ Failed to get current secret: {e}")
            # Fallback to settings.SECRET_KEY
            return settings.SECRET_KEY

    @classmethod
    async def get_all_valid_secrets(cls) -> List[str]:
        """
        Get all currently valid secrets (current + previous if in grace period)

        Returns:
            List of valid secrets
        """
        secrets_list = []

        try:
            # Get current secret
            current_secret = await redis_client.get(cls.CURRENT_SECRET_KEY)
            if current_secret:
                secrets_list.append(current_secret)

            # Get previous secret (if still in grace period)
            previous_secret = await redis_client.get(cls.PREVIOUS_SECRET_KEY)
            if previous_secret:
                secrets_list.append(previous_secret)

            # Fallback to settings secret if no secrets found
            if not secrets_list:
                logger.warning("⚠️ No secrets in Redis, using settings.SECRET_KEY")
                secrets_list.append(settings.SECRET_KEY)

            return secrets_list

        except Exception as e:
            logger.error(f"❌ Failed to get valid secrets: {e}")
            return [settings.SECRET_KEY]

    @classmethod
    async def check_and_rotate(cls) -> bool:
        """
        Check if rotation is needed and perform if necessary

        Returns:
            True if rotation was performed, False otherwise
        """
        try:
            # Get next rotation date
            next_rotation_str = await redis_client.get(cls.NEXT_ROTATION_KEY)

            if not next_rotation_str:
                logger.warning("⚠️ No rotation date found, initializing...")
                await cls.initialize()
                return False

            next_rotation = datetime.fromisoformat(next_rotation_str)
            now = datetime.utcnow()

            # Check if rotation is needed
            if now >= next_rotation:
                logger.info("🔄 JWT secret rotation due, rotating now...")
                return await cls.rotate_secret()

            # Log next rotation time
            days_until_rotation = (next_rotation - now).days
            logger.debug(f"📅 Next JWT rotation in {days_until_rotation} days")

            return False

        except Exception as e:
            logger.error(f"❌ Failed to check rotation: {e}")
            return False

    @classmethod
    async def create_token(
        cls,
        data: Dict[str, Any],
        token_type: str = "access",
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT token with current secret

        Args:
            data: Data to encode
            token_type: Token type ("access" or "refresh")
            expires_delta: Custom expiration time

        Returns:
            Encoded JWT token
        """
        try:
            # Get current secret
            secret = await cls.get_current_secret()

            if not secret:
                raise ValueError("No JWT secret available")

            # Prepare payload
            to_encode = data.copy()

            if expires_delta:
                expire = datetime.utcnow() + expires_delta
            else:
                if token_type == "access":
                    expire = datetime.utcnow() + timedelta(
                        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
                    )
                else:
                    expire = datetime.utcnow() + timedelta(
                        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
                    )

            to_encode.update({
                "exp": expire,
                "iat": datetime.utcnow(),
                "type": token_type
            })

            # Encode token
            encoded_jwt = jwt.encode(
                to_encode,
                secret,
                algorithm=settings.ALGORITHM
            )

            return encoded_jwt

        except Exception as e:
            logger.error(f"❌ Failed to create token: {e}")
            raise

    @classmethod
    async def decode_token(cls, token: str) -> Optional[Dict[str, Any]]:
        """
        Decode JWT token, trying all valid secrets

        Args:
            token: JWT token to decode

        Returns:
            Decoded payload or None if invalid
        """
        try:
            # Get all valid secrets
            valid_secrets = await cls.get_all_valid_secrets()

            # Try each secret
            for secret in valid_secrets:
                try:
                    payload = jwt.decode(
                        token,
                        secret,
                        algorithms=[settings.ALGORITHM]
                    )
                    return payload
                except JWTError:
                    continue

            # If we reach here, token is invalid with all secrets
            logger.debug("⚠️ Token invalid with all secrets")
            return None

        except Exception as e:
            logger.error(f"❌ Failed to decode token: {e}")
            return None

    @classmethod
    async def get_rotation_info(cls) -> Dict[str, Any]:
        """
        Get information about current rotation status

        Returns:
            Dictionary with rotation information
        """
        try:
            rotation_date_str = await redis_client.get(cls.ROTATION_DATE_KEY)
            next_rotation_str = await redis_client.get(cls.NEXT_ROTATION_KEY)

            rotation_date = None
            next_rotation = None

            if rotation_date_str:
                rotation_date = datetime.fromisoformat(rotation_date_str)

            if next_rotation_str:
                next_rotation = datetime.fromisoformat(next_rotation_str)

            # Check if previous secret exists (grace period active)
            previous_exists = await redis_client.exists(cls.PREVIOUS_SECRET_KEY)

            return {
                "last_rotation": rotation_date.isoformat() if rotation_date else None,
                "next_rotation": next_rotation.isoformat() if next_rotation else None,
                "days_until_rotation": (next_rotation - datetime.utcnow()).days if next_rotation else None,
                "grace_period_active": bool(previous_exists),
                "rotation_interval_days": cls.ROTATION_INTERVAL_DAYS,
                "grace_period_days": cls.GRACE_PERIOD_DAYS
            }

        except Exception as e:
            logger.error(f"❌ Failed to get rotation info: {e}")
            return {}

    @classmethod
    async def force_rotation(cls) -> bool:
        """
        Force immediate secret rotation (admin function)

        Returns:
            True if successful, False otherwise
        """
        logger.warning("🔐 Force rotation requested")
        return await cls.rotate_secret()

    @classmethod
    async def _log_rotation_event(cls, is_initial: bool = False):
        """Log rotation event to audit system"""
        try:
            from app.services.audit_service import audit_service
            from app.models.audit_log import AuditAction, AuditSeverity
            from app.core.database import get_db

            async for db in get_db():
                await audit_service.log_event(
                    db=db,
                    action=AuditAction.CONFIG_CHANGED,
                    user_id=None,
                    user_email="system",
                    user_role="system",
                    description="JWT secret initialized" if is_initial else "JWT secret rotated",
                    target_type="jwt_secret",
                    target_id="rotation",
                    details={
                        "action": "initialize" if is_initial else "rotate",
                        "rotation_interval_days": cls.ROTATION_INTERVAL_DAYS,
                        "grace_period_days": cls.GRACE_PERIOD_DAYS
                    },
                    severity=AuditSeverity.INFO
                )
                break

        except Exception as e:
            logger.error(f"❌ Failed to log rotation event: {e}")


# Background rotation task
async def jwt_rotation_background_task():
    """
    Background task to periodically check and rotate JWT secrets

    Should be run as a periodic task (e.g., daily)
    """
    logger.info("🔄 JWT rotation background task started")

    try:
        # Check and rotate if needed
        rotated = await JWTRotationManager.check_and_rotate()

        if rotated:
            logger.info("✅ JWT secret rotated by background task")
        else:
            logger.debug("ℹ️ No rotation needed")

    except Exception as e:
        logger.error(f"❌ JWT rotation background task failed: {e}")


# Export singleton instance
jwt_rotation = JWTRotationManager()
