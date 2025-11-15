"""
Orizon Zero Trust Connect - Public Provisioning Endpoints
For: Marco @ Syneto/Orizon

Public endpoints for node provisioning (no auth required)
"""

from fastapi import APIRouter, HTTPException, status, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import Depends
import jwt
from datetime import datetime

from app.core.database import get_db
from app.core.config import settings
from app.models.node import Node
from app.services.node_provision_service import NodeProvisioningService
from loguru import logger

router = APIRouter()


def verify_provision_token(token: str) -> dict:
    """
    Verify provision token and extract payload

    Args:
        token: JWT provision token

    Returns:
        Decoded payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        # Decode token
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=["HS256"]
        )

        # Check token type
        if payload.get("type") != "provision":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )

        # Check expiration
        exp = payload.get("exp")
        if not exp or datetime.utcnow().timestamp() > exp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )

        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )


@router.get("/{node_id}")
async def provision_landing_page(
    node_id: str,
    token: str = Query(..., description="Provision token from QR code"),
    db: AsyncSession = Depends(get_db),
):
    """
    Provision landing page

    This is the page users reach when scanning the QR code.
    Returns node information and download links for platform-specific scripts.

    **Public endpoint** - No authentication required, but requires valid provision token.
    """
    # Verify token
    payload = verify_provision_token(token)

    # Check if token is for this node
    token_node_id = payload.get("node_id")
    if token_node_id != node_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token is not valid for this node"
        )

    # Get node info
    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()

    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Node not found"
        )

    # Get services from token
    services = payload.get("services", [])

    # Build download URLs
    base_url = settings.API_BASE_URL
    download_urls = {
        "linux": f"{base_url}/api/v1/provision/{node_id}/script/linux?token={token}",
        "macos": f"{base_url}/api/v1/provision/{node_id}/script/macos?token={token}",
        "windows": f"{base_url}/api/v1/provision/{node_id}/script/windows?token={token}",
    }

    logger.info(f"📱 Provision page accessed for node: {node.name} (ID: {node_id})")

    return {
        "node_id": node_id,
        "node_name": node.name,
        "node_type": node.node_type,
        "status": node.status,
        "services": services,
        "download_urls": download_urls,
        "expires_at": datetime.fromtimestamp(payload.get("exp")),
        "instructions": {
            "linux": "Download and run: chmod +x setup.sh && sudo ./setup.sh",
            "macos": "Download and run: chmod +x setup.sh && sudo ./setup.sh",
            "windows": "Download and run as Administrator: powershell -ExecutionPolicy Bypass -File setup.ps1",
        }
    }


@router.get("/{node_id}/script/{os_type}")
async def download_provision_script(
    node_id: str,
    os_type: str,
    token: str = Query(..., description="Provision token"),
    db: AsyncSession = Depends(get_db),
):
    """
    Download platform-specific provision script

    **Public endpoint** - No authentication required, but requires valid provision token.

    Args:
        node_id: Node ID
        os_type: Platform type (linux, macos, windows)
        token: Provision token from QR code

    Returns:
        Script file (bash for Linux/macOS, PowerShell for Windows)
    """
    # Validate os_type
    valid_os_types = ["linux", "macos", "windows"]
    if os_type not in valid_os_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid os_type. Must be one of: {', '.join(valid_os_types)}"
        )

    # Verify token
    payload = verify_provision_token(token)

    # Check if token is for this node
    token_node_id = payload.get("node_id")
    if token_node_id != node_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token is not valid for this node"
        )

    # Get node info
    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()

    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Node not found"
        )

    # Get services from token
    services = payload.get("services", [])

    # Initialize provisioning service
    provision_service = NodeProvisioningService(
        api_base_url=settings.API_BASE_URL,
        hub_host=settings.HUB_HOST,
        hub_ssh_port=settings.HUB_SSH_PORT,
    )

    # Generate script
    try:
        if os_type == "linux":
            script = provision_service.generate_linux_script(
                node_id=node_id,
                node_name=node.name,
                provision_token=token,
                services=services,
            )
            media_type = "text/x-shellscript"
            filename = "orizon-setup.sh"

        elif os_type == "macos":
            script = provision_service.generate_macos_script(
                node_id=node_id,
                node_name=node.name,
                provision_token=token,
                services=services,
            )
            media_type = "text/x-shellscript"
            filename = "orizon-setup.sh"

        elif os_type == "windows":
            script = provision_service.generate_windows_script(
                node_id=node_id,
                node_name=node.name,
                provision_token=token,
                services=services,
            )
            media_type = "text/plain"
            filename = "orizon-setup.ps1"

        logger.info(f"📥 Script downloaded for {os_type}: {node.name} (ID: {node_id})")

        # Return script as downloadable file
        return Response(
            content=script,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except Exception as e:
        logger.error(f"❌ Failed to generate script: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate script: {str(e)}"
        )
