"""
Orizon Zero Trust Connect - Two-Factor Authentication API Endpoints
For: Marco @ Syneto/Orizon
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List
from loguru import logger

from app.core.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.services.totp_service import totp_service
from app.middleware.rate_limit import rate_limit

router = APIRouter()


class TOTPSetupResponse(BaseModel):
    """TOTP setup response"""
    secret: str
    qr_code: str
    issuer: str = "Orizon Zero Trust"


class TOTPVerifyRequest(BaseModel):
    """TOTP verification request"""
    token: str


class BackupCodesResponse(BaseModel):
    """Backup codes response"""
    codes: List[str]
    message: str


@router.post("/setup", response_model=TOTPSetupResponse)
@rate_limit("5/hour")
async def setup_2fa(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Setup 2FA for current user

    Generates TOTP secret and QR code for enrollment
    """
    try:
        # Generate secret
        secret = await totp_service.generate_secret(db, str(current_user.id))

        if not secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate 2FA secret"
            )

        # Generate QR code
        qr_code = await totp_service.generate_qr_code(db, str(current_user.id))

        if not qr_code:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate QR code"
            )

        logger.info(f"✅ 2FA setup initiated for user {current_user.email}")

        return TOTPSetupResponse(
            secret=secret,
            qr_code=qr_code
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error setting up 2FA: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/verify")
@rate_limit("10/minute")
async def verify_2fa_token(
    verify_data: TOTPVerifyRequest,
    enable_on_success: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Verify TOTP token

    If enable_on_success=True, enables 2FA after successful verification (enrollment)
    """
    try:
        # Verify token
        is_valid = await totp_service.verify_totp(
            db=db,
            user_id=str(current_user.id),
            token=verify_data.token,
            enable_on_success=enable_on_success
        )

        if not is_valid:
            logger.warning(f"⚠️ Invalid 2FA token for user {current_user.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid 2FA token"
            )

        logger.info(f"✅ 2FA token verified for user {current_user.email}")

        return {
            "message": "2FA token verified successfully",
            "2fa_enabled": enable_on_success
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error verifying 2FA token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/disable")
@rate_limit("5/hour")
async def disable_2fa(
    verify_data: TOTPVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Disable 2FA for current user

    Requires valid TOTP token to confirm
    """
    try:
        # Verify token before disabling
        is_valid = await totp_service.verify_totp(
            db=db,
            user_id=str(current_user.id),
            token=verify_data.token,
            enable_on_success=False
        )

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid 2FA token. Cannot disable 2FA."
            )

        # Disable 2FA
        success = await totp_service.disable_2fa(db, str(current_user.id))

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to disable 2FA"
            )

        logger.info(f"✅ 2FA disabled for user {current_user.email}")

        return {"message": "2FA disabled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error disabling 2FA: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/backup-codes", response_model=BackupCodesResponse)
@rate_limit("3/day")
async def generate_backup_codes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate backup codes for account recovery

    WARNING: Backup codes are shown only once. Save them securely!
    """
    try:
        # Check if 2FA is enabled
        if not current_user.totp_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA must be enabled before generating backup codes"
            )

        # Generate codes
        backup_codes = await totp_service.generate_backup_codes(
            db=db,
            user_id=str(current_user.id)
        )

        if not backup_codes:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate backup codes"
            )

        logger.info(f"✅ Backup codes generated for user {current_user.email}")

        return BackupCodesResponse(
            codes=backup_codes,
            message="Save these codes securely. They will not be shown again!"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generating backup codes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/backup-codes/verify")
@rate_limit("10/hour")
async def verify_backup_code(
    verify_data: TOTPVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Verify backup code (one-time use)

    Used for account recovery when 2FA device is unavailable
    """
    try:
        # Verify backup code
        is_valid = await totp_service.verify_backup_code(
            db=db,
            user_id=str(current_user.id),
            backup_code=verify_data.token
        )

        if not is_valid:
            logger.warning(f"⚠️ Invalid backup code for user {current_user.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid backup code"
            )

        logger.info(f"✅ Backup code verified and consumed for user {current_user.email}")

        return {
            "message": "Backup code verified successfully. This code has been consumed and cannot be reused."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error verifying backup code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
