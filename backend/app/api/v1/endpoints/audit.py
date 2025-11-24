"""
Orizon Zero Trust Connect - Audit Logs API Endpoints
For: Marco @ Syneto/Orizon
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime
from loguru import logger

from app.core.database import get_db
from app.auth.dependencies import require_role
from app.models.user import User, UserRole
from app.models.audit_log import AuditAction, AuditSeverity
from app.services.audit_service import audit_service
from app.middleware.rate_limit import rate_limit

router = APIRouter()


@router.get("/")
@rate_limit("100/minute")
async def get_audit_logs(
    request: Request,
    user_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    target_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    Query audit logs with filters

    Requires: Super Admin role or higher
    """
    try:
        # Convert string enums
        action_enum = AuditAction(action) if action else None
        severity_enum = AuditSeverity(severity) if severity else None

        # Query logs
        logs, total_count = await audit_service.get_audit_logs(
            db=db,
            user_id=user_id,
            action=action_enum,
            target_type=target_type,
            severity=severity_enum,
            start_date=start_date,
            end_date=end_date,
            search_query=search,
            skip=skip,
            limit=limit
        )

        # Convert to dict
        logs_dict = [log.to_dict() for log in logs]

        return {
            "logs": logs_dict,
            "total": total_count,
            "skip": skip,
            "limit": limit
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid parameter value: {str(e)}"
        )
    except Exception as e:
        logger.error(f"❌ Error querying audit logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/export")
@rate_limit("5/minute")
async def export_audit_logs(
    request: Request,
    format: str = Query("json", regex="^(json|csv|siem)$"),
    user_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(require_role(UserRole.SUPERUSER)),
    db: AsyncSession = Depends(get_db)
):
    """
    Export audit logs in various formats (JSON, CSV, SIEM/CEF)

    Requires: SuperUser role
    """
    try:
        # Convert string enum
        action_enum = AuditAction(action) if action else None

        # Export logs
        export_data = await audit_service.export_audit_logs(
            db=db,
            format=format,
            user_id=user_id,
            action=action_enum,
            start_date=start_date,
            end_date=end_date
        )

        if not export_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No audit logs found matching criteria"
            )

        # Determine content type and filename
        content_types = {
            "json": "application/json",
            "csv": "text/csv",
            "siem": "text/plain"
        }

        filename_extensions = {
            "json": "json",
            "csv": "csv",
            "siem": "cef"
        }

        content_type = content_types.get(format, "application/octet-stream")
        filename = f"audit_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{filename_extensions[format]}"

        logger.info(f"✅ Audit logs exported by {current_user.email} (format={format})")

        return Response(
            content=export_data,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid parameter value: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error exporting audit logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/statistics")
@rate_limit("30/minute")
async def get_audit_statistics(
    request: Request,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    Get audit log statistics for a period

    Requires: Super Admin role or higher
    """
    try:
        stats = await audit_service.get_audit_statistics(
            db=db,
            start_date=start_date,
            end_date=end_date
        )

        return stats

    except Exception as e:
        logger.error(f"❌ Error getting audit statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/cleanup")
@rate_limit("1/hour")
async def cleanup_old_audit_logs(
    request: Request,
    retention_days: int = Query(90, ge=1, le=365),
    current_user: User = Depends(require_role(UserRole.SUPERUSER)),
    db: AsyncSession = Depends(get_db)
):
    """
    Cleanup audit logs older than retention period

    Requires: SuperUser role
    """
    try:
        deleted_count = await audit_service.cleanup_old_logs(
            db=db,
            retention_days=retention_days
        )

        logger.info(
            f"✅ Audit logs cleanup completed by {current_user.email}: "
            f"{deleted_count} logs deleted (retention={retention_days} days)"
        )

        return {
            "message": "Audit logs cleanup completed",
            "deleted_count": deleted_count,
            "retention_days": retention_days
        }

    except Exception as e:
        logger.error(f"❌ Error cleaning up audit logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
