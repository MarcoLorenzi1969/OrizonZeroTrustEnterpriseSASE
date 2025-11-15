"""
Orizon Zero Trust Connect - TOTP 2FA Service
For: Marco @ Syneto/Orizon

Time-based One-Time Password (TOTP) two-factor authentication service
Compatible with Google Authenticator, Authy, Microsoft Authenticator, etc.
"""

import pyotp
import qrcode
import io
import base64
from typing import Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.models.user import User
from app.core.redis import redis_client
from app.core.config import settings


class TOTPService:
    """
    TOTP Two-Factor Authentication Service

    Features:
    - Generate TOTP secrets for users
    - Generate QR codes for easy enrollment
    - Verify TOTP tokens with window tolerance
    - Backup codes for account recovery
    - Rate limiting to prevent brute force
    - Redis caching for performance
    """

    # TOTP settings
    ISSUER_NAME = "Orizon Zero Trust"
    TOTP_INTERVAL = 30  # 30 seconds per token
    TOTP_DIGITS = 6  # 6-digit codes
    VERIFICATION_WINDOW = 1  # Allow 1 step before/after (±30s tolerance)

    # Rate limiting
    MAX_VERIFICATION_ATTEMPTS = 5
    RATE_LIMIT_WINDOW = 300  # 5 minutes

    # Backup codes
    BACKUP_CODE_COUNT = 10
    BACKUP_CODE_LENGTH = 8

    async def generate_secret(
        self,
        db: AsyncSession,
        user_id: str
    ) -> Optional[str]:
        """
        Generate TOTP secret for user

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Base32-encoded secret or None on failure
        """
        try:
            # Get user
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                logger.error(f"❌ User {user_id} not found")
                return None

            # Generate secret
            secret = pyotp.random_base32()

            # Store secret in user record (encrypted in production!)
            user.totp_secret = secret
            user.totp_enabled = False  # Will be enabled after first successful verification
            user.totp_created_at = datetime.utcnow()

            await db.commit()

            # Cache secret in Redis for quick access
            await redis_client.set_with_expiry(
                f"totp_secret:{user_id}",
                secret,
                expiry=3600  # 1 hour
            )

            logger.info(f"✅ Generated TOTP secret for user {user.email}")

            return secret

        except Exception as e:
            logger.error(f"❌ Failed to generate TOTP secret: {e}")
            await db.rollback()
            return None

    async def get_secret(
        self,
        db: AsyncSession,
        user_id: str
    ) -> Optional[str]:
        """
        Get user's TOTP secret

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Base32-encoded secret or None
        """
        try:
            # Try Redis cache first
            cached_secret = await redis_client.get(f"totp_secret:{user_id}")
            if cached_secret:
                return cached_secret

            # Fallback to database
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user or not user.totp_secret:
                return None

            # Cache for next time
            await redis_client.set_with_expiry(
                f"totp_secret:{user_id}",
                user.totp_secret,
                expiry=3600
            )

            return user.totp_secret

        except Exception as e:
            logger.error(f"❌ Failed to get TOTP secret: {e}")
            return None

    async def verify_totp(
        self,
        db: AsyncSession,
        user_id: str,
        token: str,
        enable_on_success: bool = True
    ) -> bool:
        """
        Verify TOTP token

        Args:
            db: Database session
            user_id: User ID
            token: 6-digit TOTP token
            enable_on_success: Enable 2FA if verification succeeds (for enrollment)

        Returns:
            True if token is valid, False otherwise
        """
        try:
            # Check rate limiting
            if not await self._check_rate_limit(user_id):
                logger.warning(f"⚠️ Rate limit exceeded for 2FA verification (user {user_id})")
                return False

            # Get user's secret
            secret = await self.get_secret(db, user_id)
            if not secret:
                logger.error(f"❌ No TOTP secret found for user {user_id}")
                return False

            # Create TOTP object
            totp = pyotp.TOTP(
                secret,
                interval=self.TOTP_INTERVAL,
                digits=self.TOTP_DIGITS
            )

            # Verify token with window tolerance
            is_valid = totp.verify(
                token,
                valid_window=self.VERIFICATION_WINDOW
            )

            if is_valid:
                # Token is valid
                logger.info(f"✅ TOTP verification successful for user {user_id}")

                # Enable 2FA if this is enrollment
                if enable_on_success:
                    await self._enable_2fa(db, user_id)

                # Reset rate limit counter
                await redis_client.delete(f"totp_attempts:{user_id}")

                return True
            else:
                # Token is invalid
                logger.warning(f"⚠️ Invalid TOTP token for user {user_id}")
                return False

        except Exception as e:
            logger.error(f"❌ Failed to verify TOTP: {e}")
            return False

    async def generate_qr_code(
        self,
        db: AsyncSession,
        user_id: str
    ) -> Optional[str]:
        """
        Generate QR code for TOTP enrollment

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Base64-encoded QR code image (PNG) or None
        """
        try:
            # Get user
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                logger.error(f"❌ User {user_id} not found")
                return None

            # Get or generate secret
            secret = user.totp_secret
            if not secret:
                secret = await self.generate_secret(db, user_id)
                if not secret:
                    return None

            # Create provisioning URI
            totp = pyotp.TOTP(secret)
            provisioning_uri = totp.provisioning_uri(
                name=user.email,
                issuer_name=self.ISSUER_NAME
            )

            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(provisioning_uri)
            qr.make(fit=True)

            # Create image
            img = qr.make_image(fill_color="black", back_color="white")

            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)

            img_base64 = base64.b64encode(buffer.read()).decode('utf-8')

            logger.info(f"✅ Generated QR code for user {user.email}")

            return f"data:image/png;base64,{img_base64}"

        except Exception as e:
            logger.error(f"❌ Failed to generate QR code: {e}")
            return None

    async def disable_2fa(
        self,
        db: AsyncSession,
        user_id: str
    ) -> bool:
        """
        Disable 2FA for user

        Args:
            db: Database session
            user_id: User ID

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get user
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                logger.error(f"❌ User {user_id} not found")
                return False

            # Disable 2FA
            user.totp_enabled = False
            user.totp_secret = None
            user.totp_created_at = None

            await db.commit()

            # Clear Redis cache
            await redis_client.delete(f"totp_secret:{user_id}")

            logger.info(f"✅ Disabled 2FA for user {user.email}")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to disable 2FA: {e}")
            await db.rollback()
            return False

    async def generate_backup_codes(
        self,
        db: AsyncSession,
        user_id: str
    ) -> Optional[list[str]]:
        """
        Generate backup codes for account recovery

        Args:
            db: Database session
            user_id: User ID

        Returns:
            List of backup codes or None on failure
        """
        try:
            import secrets
            import string

            # Generate random backup codes
            alphabet = string.ascii_uppercase + string.digits
            backup_codes = [
                ''.join(secrets.choice(alphabet) for _ in range(self.BACKUP_CODE_LENGTH))
                for _ in range(self.BACKUP_CODE_COUNT)
            ]

            # Format codes with dashes for readability
            formatted_codes = [
                f"{code[:4]}-{code[4:]}" for code in backup_codes
            ]

            # Hash codes for storage (bcrypt)
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

            hashed_codes = [
                pwd_context.hash(code) for code in backup_codes
            ]

            # Store hashed codes in user record
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                return None

            # Store as JSON array in database
            import json
            user.backup_codes = json.dumps(hashed_codes)

            await db.commit()

            logger.info(f"✅ Generated {len(formatted_codes)} backup codes for user {user.email}")

            # Return unhashed codes to show to user (one-time only!)
            return formatted_codes

        except Exception as e:
            logger.error(f"❌ Failed to generate backup codes: {e}")
            await db.rollback()
            return None

    async def verify_backup_code(
        self,
        db: AsyncSession,
        user_id: str,
        backup_code: str
    ) -> bool:
        """
        Verify and consume a backup code

        Args:
            db: Database session
            user_id: User ID
            backup_code: Backup code to verify

        Returns:
            True if valid, False otherwise
        """
        try:
            import json
            from passlib.context import CryptContext

            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

            # Get user
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user or not user.backup_codes:
                return False

            # Load backup codes
            hashed_codes = json.loads(user.backup_codes)

            # Remove dashes from input
            backup_code = backup_code.replace("-", "")

            # Check each code
            for i, hashed_code in enumerate(hashed_codes):
                if pwd_context.verify(backup_code, hashed_code):
                    # Code is valid - remove it (one-time use)
                    hashed_codes.pop(i)
                    user.backup_codes = json.dumps(hashed_codes)
                    await db.commit()

                    logger.info(f"✅ Backup code verified and consumed for user {user.email}")
                    return True

            logger.warning(f"⚠️ Invalid backup code for user {user.email}")
            return False

        except Exception as e:
            logger.error(f"❌ Failed to verify backup code: {e}")
            return False

    async def _enable_2fa(
        self,
        db: AsyncSession,
        user_id: str
    ):
        """Enable 2FA for user after successful enrollment"""
        try:
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if user:
                user.totp_enabled = True
                await db.commit()

                logger.info(f"✅ Enabled 2FA for user {user.email}")

        except Exception as e:
            logger.error(f"❌ Failed to enable 2FA: {e}")

    async def _check_rate_limit(self, user_id: str) -> bool:
        """
        Check rate limit for TOTP verification attempts

        Args:
            user_id: User ID

        Returns:
            True if within limit, False if exceeded
        """
        try:
            key = f"totp_attempts:{user_id}"

            # Get current attempts
            attempts = await redis_client.get(key)

            if attempts is None:
                # First attempt
                await redis_client.set_with_expiry(
                    key,
                    "1",
                    expiry=self.RATE_LIMIT_WINDOW
                )
                return True

            attempts = int(attempts)

            if attempts >= self.MAX_VERIFICATION_ATTEMPTS:
                # Rate limit exceeded
                return False

            # Increment attempts
            await redis_client.increment(key)
            return True

        except Exception as e:
            logger.error(f"❌ Error checking rate limit: {e}")
            return True  # Fail open


# Global TOTP service instance
totp_service = TOTPService()
