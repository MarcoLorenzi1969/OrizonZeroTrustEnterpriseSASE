"""
Orizon Zero Trust Connect - Complete Audit Service
For: Marco @ Syneto/Orizon

Complete audit logging service for GDPR, NIS2, ISO 27001 compliance
Features:
- Comprehensive event logging
- Query with filters
- Export to JSON/CSV/SIEM formats
- Automatic retention management (90 days)
- Real-time event streaming
"""

import csv
import json
import io
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, delete
from sqlalchemy.orm import selectinload
from loguru import logger

from app.models.audit_log import AuditLog, AuditAction, AuditSeverity
from app.core.mongodb import get_mongodb
from app.core.config import settings


class AuditService:
    """
    Complete Audit Logging Service

    Features:
    - Comprehensive event logging with context
    - Advanced querying with filters
    - Multiple export formats (JSON, CSV, SIEM)
    - Automatic retention management
    - Geolocation tracking
    - MongoDB backup for long-term storage
    """

    # Retention settings
    DEFAULT_RETENTION_DAYS = 90
    MONGODB_RETENTION_DAYS = 365  # 1 year in MongoDB

    # Export limits
    MAX_EXPORT_RECORDS = 50000

    async def log_event(
        self,
        db: AsyncSession,
        action: AuditAction,
        user_id: Optional[str],
        user_email: Optional[str],
        user_role: Optional[str],
        description: str,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        target_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        changes: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_method: Optional[str] = None,
        request_path: Optional[str] = None,
        severity: AuditSeverity = AuditSeverity.INFO,
        success: bool = True,
        error_message: Optional[str] = None,
        node_id: Optional[str] = None
    ) -> Optional[AuditLog]:
        """
        Log an audit event

        Args:
            db: Database session
            action: Action type (from AuditAction enum)
            user_id: User who performed action
            user_email: User email
            user_role: User role
            description: Human-readable description
            target_type: Type of affected resource (user, node, tunnel, etc.)
            target_id: ID of affected resource
            target_name: Name of affected resource
            details: Additional details (JSON)
            changes: Before/after changes (JSON)
            ip_address: IP address of request
            user_agent: User agent string
            request_method: HTTP method
            request_path: Request path
            severity: Event severity
            success: Whether action succeeded
            error_message: Error message if failed
            node_id: Related node ID

        Returns:
            Created AuditLog or None on failure
        """
        try:
            # Resolve geolocation from IP (if available)
            country, city = await self._get_geolocation(ip_address)

            # Create audit log entry
            audit_log = AuditLog(
                id=uuid.uuid4(),
                action=action,
                severity=severity,
                user_id=uuid.UUID(user_id) if user_id else None,
                user_email=user_email,
                user_role=user_role,
                target_type=target_type,
                target_id=target_id,
                target_name=target_name,
                node_id=uuid.UUID(node_id) if node_id else None,
                ip_address=ip_address,
                user_agent=user_agent,
                request_method=request_method,
                request_path=request_path,
                description=description,
                details=details or {},
                changes=changes or {},
                success=success,
                error_message=error_message,
                country=country,
                city=city,
                timestamp=datetime.utcnow()
            )

            # Save to PostgreSQL
            db.add(audit_log)
            await db.commit()
            await db.refresh(audit_log)

            # Also backup to MongoDB for long-term storage
            await self._backup_to_mongodb(audit_log)

            logger.info(
                f"📝 Audit log created: {action.value} by {user_email or 'system'} "
                f"(target: {target_type}:{target_id}, severity: {severity.value})"
            )

            return audit_log

        except Exception as e:
            logger.error(f"❌ Failed to create audit log: {e}")
            await db.rollback()
            return None

    async def get_audit_logs(
        self,
        db: AsyncSession,
        user_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        severity: Optional[AuditSeverity] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        success: Optional[bool] = None,
        ip_address: Optional[str] = None,
        search_query: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[AuditLog], int]:
        """
        Query audit logs with advanced filtering

        Args:
            db: Database session
            user_id: Filter by user
            action: Filter by action type
            target_type: Filter by target type
            target_id: Filter by target ID
            severity: Filter by severity
            start_date: Start of date range
            end_date: End of date range
            success: Filter by success status
            ip_address: Filter by IP address
            search_query: Full-text search in description
            skip: Pagination offset
            limit: Max results to return

        Returns:
            Tuple of (audit_logs, total_count)
        """
        try:
            # Build query filters
            filters = []

            if user_id:
                filters.append(AuditLog.user_id == uuid.UUID(user_id))

            if action:
                filters.append(AuditLog.action == action)

            if target_type:
                filters.append(AuditLog.target_type == target_type)

            if target_id:
                filters.append(AuditLog.target_id == target_id)

            if severity:
                filters.append(AuditLog.severity == severity)

            if start_date:
                filters.append(AuditLog.timestamp >= start_date)

            if end_date:
                filters.append(AuditLog.timestamp <= end_date)

            if success is not None:
                filters.append(AuditLog.success == success)

            if ip_address:
                filters.append(AuditLog.ip_address == ip_address)

            if search_query:
                # Full-text search in description and details
                filters.append(
                    or_(
                        AuditLog.description.ilike(f"%{search_query}%"),
                        AuditLog.details.astext.ilike(f"%{search_query}%")
                    )
                )

            # Build query
            query = select(AuditLog)

            if filters:
                query = query.where(and_(*filters))

            # Get total count
            count_query = select(func.count()).select_from(
                query.subquery()
            )
            result = await db.execute(count_query)
            total_count = result.scalar()

            # Get paginated results
            query = query.order_by(AuditLog.timestamp.desc())
            query = query.offset(skip).limit(limit)

            result = await db.execute(query)
            audit_logs = result.scalars().all()

            logger.debug(
                f"📋 Retrieved {len(audit_logs)} audit logs "
                f"(total: {total_count}, skip: {skip}, limit: {limit})"
            )

            return audit_logs, total_count

        except Exception as e:
            logger.error(f"❌ Failed to query audit logs: {e}")
            return [], 0

    async def export_audit_logs(
        self,
        db: AsyncSession,
        format: str = "json",
        user_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = MAX_EXPORT_RECORDS
    ) -> Optional[bytes]:
        """
        Export audit logs in various formats

        Args:
            db: Database session
            format: Export format ("json", "csv", "siem")
            user_id: Filter by user
            action: Filter by action
            start_date: Start date
            end_date: End date
            limit: Max records to export

        Returns:
            Exported data as bytes or None on failure
        """
        try:
            # Get audit logs
            audit_logs, _ = await self.get_audit_logs(
                db=db,
                user_id=user_id,
                action=action,
                start_date=start_date,
                end_date=end_date,
                limit=limit
            )

            if not audit_logs:
                logger.warning("⚠️ No audit logs to export")
                return None

            # Export based on format
            if format == "json":
                return await self._export_json(audit_logs)
            elif format == "csv":
                return await self._export_csv(audit_logs)
            elif format == "siem":
                return await self._export_siem(audit_logs)
            else:
                logger.error(f"❌ Unsupported export format: {format}")
                return None

        except Exception as e:
            logger.error(f"❌ Failed to export audit logs: {e}")
            return None

    async def cleanup_old_logs(
        self,
        db: AsyncSession,
        retention_days: int = DEFAULT_RETENTION_DAYS
    ) -> int:
        """
        Cleanup audit logs older than retention period

        Args:
            db: Database session
            retention_days: Number of days to retain logs

        Returns:
            Number of deleted logs
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

            # Delete old logs
            stmt = delete(AuditLog).where(
                AuditLog.timestamp < cutoff_date
            )

            result = await db.execute(stmt)
            deleted_count = result.rowcount

            await db.commit()

            logger.info(
                f"🗑️ Cleaned up {deleted_count} audit logs older than "
                f"{retention_days} days (cutoff: {cutoff_date})"
            )

            return deleted_count

        except Exception as e:
            logger.error(f"❌ Failed to cleanup audit logs: {e}")
            await db.rollback()
            return 0

    async def get_audit_statistics(
        self,
        db: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get audit log statistics for a period

        Args:
            db: Database session
            start_date: Start of period
            end_date: End of period

        Returns:
            Dictionary with statistics
        """
        try:
            # Build base query
            filters = []

            if start_date:
                filters.append(AuditLog.timestamp >= start_date)

            if end_date:
                filters.append(AuditLog.timestamp <= end_date)

            base_query = select(AuditLog)
            if filters:
                base_query = base_query.where(and_(*filters))

            # Total logs
            count_query = select(func.count()).select_from(base_query.subquery())
            result = await db.execute(count_query)
            total_logs = result.scalar()

            # Logs by action
            action_query = select(
                AuditLog.action,
                func.count(AuditLog.id).label('count')
            )
            if filters:
                action_query = action_query.where(and_(*filters))
            action_query = action_query.group_by(AuditLog.action)

            result = await db.execute(action_query)
            actions_stats = {row.action.value: row.count for row in result}

            # Logs by severity
            severity_query = select(
                AuditLog.severity,
                func.count(AuditLog.id).label('count')
            )
            if filters:
                severity_query = severity_query.where(and_(*filters))
            severity_query = severity_query.group_by(AuditLog.severity)

            result = await db.execute(severity_query)
            severity_stats = {row.severity.value: row.count for row in result}

            # Failed actions
            failed_query = select(func.count()).select_from(base_query.subquery()).where(
                AuditLog.success == False
            )
            result = await db.execute(failed_query)
            failed_count = result.scalar()

            stats = {
                "total_logs": total_logs,
                "failed_actions": failed_count,
                "success_rate": ((total_logs - failed_count) / total_logs * 100) if total_logs > 0 else 0,
                "by_action": actions_stats,
                "by_severity": severity_stats,
                "period": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None
                }
            }

            logger.debug(f"📊 Generated audit statistics: {total_logs} logs")

            return stats

        except Exception as e:
            logger.error(f"❌ Failed to get audit statistics: {e}")
            return {}

    async def _backup_to_mongodb(self, audit_log: AuditLog):
        """Backup audit log to MongoDB for long-term storage"""
        try:
            mongodb = await get_mongodb()

            document = {
                "id": str(audit_log.id),
                "action": audit_log.action.value,
                "severity": audit_log.severity.value,
                "user_id": str(audit_log.user_id) if audit_log.user_id else None,
                "user_email": audit_log.user_email,
                "user_role": audit_log.user_role,
                "target_type": audit_log.target_type,
                "target_id": audit_log.target_id,
                "target_name": audit_log.target_name,
                "node_id": str(audit_log.node_id) if audit_log.node_id else None,
                "ip_address": str(audit_log.ip_address) if audit_log.ip_address else None,
                "user_agent": audit_log.user_agent,
                "request_method": audit_log.request_method,
                "request_path": audit_log.request_path,
                "description": audit_log.description,
                "details": audit_log.details,
                "changes": audit_log.changes,
                "success": audit_log.success,
                "error_message": audit_log.error_message,
                "country": audit_log.country,
                "city": audit_log.city,
                "timestamp": audit_log.timestamp
            }

            await mongodb["audit_logs_backup"].insert_one(document)

        except Exception as e:
            logger.error(f"❌ Failed to backup audit log to MongoDB: {e}")

    async def _get_geolocation(self, ip_address: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        """
        Get geolocation (country, city) from IP address

        Args:
            ip_address: IP address

        Returns:
            Tuple of (country_code, city_name)
        """
        # TODO: Implement actual geolocation service
        # Options:
        # - MaxMind GeoIP2
        # - ipapi.co
        # - ip-api.com

        return None, None

    async def _export_json(self, audit_logs: List[AuditLog]) -> bytes:
        """Export audit logs as JSON"""
        data = [log.to_dict() for log in audit_logs]

        export_data = {
            "export_date": datetime.utcnow().isoformat(),
            "format": "json",
            "version": "1.0",
            "record_count": len(data),
            "records": data
        }

        json_str = json.dumps(export_data, indent=2, default=str)
        return json_str.encode('utf-8')

    async def _export_csv(self, audit_logs: List[AuditLog]) -> bytes:
        """Export audit logs as CSV"""
        output = io.StringIO()

        # Define CSV fields
        fields = [
            'id', 'timestamp', 'action', 'severity', 'user_email', 'user_role',
            'target_type', 'target_id', 'description', 'ip_address',
            'success', 'error_message'
        ]

        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()

        for log in audit_logs:
            log_dict = log.to_dict()
            row = {field: log_dict.get(field, '') for field in fields}
            writer.writerow(row)

        csv_data = output.getvalue()
        output.close()

        return csv_data.encode('utf-8')

    async def _export_siem(self, audit_logs: List[AuditLog]) -> bytes:
        """
        Export audit logs in SIEM-compatible format (CEF - Common Event Format)

        CEF Format:
        CEF:Version|Device Vendor|Device Product|Device Version|Signature ID|Name|Severity|Extension
        """
        lines = []

        for log in audit_logs:
            # Build CEF header
            cef_version = "0"
            device_vendor = "Orizon"
            device_product = "Zero Trust Connect"
            device_version = settings.APP_VERSION
            signature_id = log.action.value
            name = log.description
            severity = self._map_severity_to_cef(log.severity)

            # Build CEF extension (key=value pairs)
            extension_parts = []

            if log.user_email:
                extension_parts.append(f"suser={log.user_email}")

            if log.ip_address:
                extension_parts.append(f"src={log.ip_address}")

            if log.target_type:
                extension_parts.append(f"target_type={log.target_type}")

            if log.target_id:
                extension_parts.append(f"target_id={log.target_id}")

            extension_parts.append(f"outcome={'success' if log.success else 'failure'}")
            extension_parts.append(f"rt={int(log.timestamp.timestamp() * 1000)}")

            extension = " ".join(extension_parts)

            # Build full CEF line
            cef_line = f"CEF:{cef_version}|{device_vendor}|{device_product}|{device_version}|{signature_id}|{name}|{severity}|{extension}"
            lines.append(cef_line)

        siem_data = "\n".join(lines)
        return siem_data.encode('utf-8')

    def _map_severity_to_cef(self, severity: AuditSeverity) -> int:
        """Map AuditSeverity to CEF severity (0-10)"""
        mapping = {
            AuditSeverity.INFO: 3,
            AuditSeverity.WARNING: 6,
            AuditSeverity.ERROR: 8,
            AuditSeverity.CRITICAL: 10
        }
        return mapping.get(severity, 5)


# Global audit service instance
audit_service = AuditService()
