"""
Unit tests for RBAC Permission Service

Tests for app.services.permission_service covering:
- User permission granting and revoking
- Access control checking (IP whitelist, expiration, service types)
- Group-based permissions
- Access logging
- Tunnel session management
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import select

from app.services.permission_service import PermissionService
from app.models.user import User
from app.models.node import Node
from app.models.user_permissions import (
    user_node_permissions,
    PermissionLevel,
    ServiceType,
    AccessLog,
    TunnelSession,
    GroupNodePermission
)
from app.models.group import Group, UserGroup


@pytest.mark.asyncio
class TestUserPermissions:
    """Test user permission granting and revoking"""

    async def test_grant_user_permission_new(self, db_session, superuser, test_node_a):
        """
        Test granting new permission to user

        Given: User and node exist
        When: Granting SSH permission
        Then: Permission should be created with correct attributes
        """
        services = {"ssh": True, "rdp": False, "vnc": False, "http": False, "https": False}

        result = await PermissionService.grant_user_permission(
            db=db_session,
            user_id=superuser.id,
            node_id=test_node_a.id,
            granted_by_id=superuser.id,
            permission_level=PermissionLevel.CONNECT,
            services=services,
            notes="Test SSH access"
        )

        assert result["user_id"] == superuser.id
        assert result["node_id"] == test_node_a.id
        assert result["permission_level"] == PermissionLevel.CONNECT
        assert result["services"]["ssh"] is True

        # Verify in database
        perm_result = await db_session.execute(
            select(user_node_permissions).where(
                user_node_permissions.c.user_id == superuser.id
            )
        )
        perm = perm_result.first()
        assert perm is not None
        assert perm.can_ssh is True
        assert perm.can_rdp is False

    async def test_grant_user_permission_update_existing(self, db_session, superuser, test_node_a):
        """
        Test updating existing permission

        Given: User already has VIEW_ONLY permission
        When: Granting FULL_CONTROL permission
        Then: Permission should be updated, not duplicated
        """
        # Grant initial permission
        services_view = {"ssh": False, "rdp": False, "vnc": False, "http": False, "https": False}
        await PermissionService.grant_user_permission(
            db=db_session,
            user_id=superuser.id,
            node_id=test_node_a.id,
            granted_by_id=superuser.id,
            permission_level=PermissionLevel.VIEW_ONLY,
            services=services_view
        )

        # Update with full control
        services_full = {"ssh": True, "rdp": True, "vnc": True, "http": True, "https": True}
        result = await PermissionService.grant_user_permission(
            db=db_session,
            user_id=superuser.id,
            node_id=test_node_a.id,
            granted_by_id=superuser.id,
            permission_level=PermissionLevel.FULL_CONTROL,
            services=services_full
        )

        assert result["permission_level"] == PermissionLevel.FULL_CONTROL

        # Verify only one permission exists
        perm_result = await db_session.execute(
            select(user_node_permissions).where(
                user_node_permissions.c.user_id == superuser.id
            )
        )
        perms = perm_result.all()
        assert len(perms) == 1
        assert perms[0].permission_level == PermissionLevel.FULL_CONTROL
        assert perms[0].can_ssh is True

    async def test_grant_permission_with_expiration(self, db_session, superuser, test_node_a):
        """
        Test granting permission with expiration date

        Given: User and node
        When: Granting permission with expires_at
        Then: Permission should have expiration set
        """
        services = {"ssh": True, "rdp": False, "vnc": False, "http": False, "https": False}
        expires_at = datetime.utcnow() + timedelta(days=30)

        await PermissionService.grant_user_permission(
            db=db_session,
            user_id=superuser.id,
            node_id=test_node_a.id,
            granted_by_id=superuser.id,
            permission_level=PermissionLevel.CONNECT,
            services=services,
            expires_at=expires_at
        )

        perm_result = await db_session.execute(
            select(user_node_permissions).where(
                user_node_permissions.c.user_id == superuser.id
            )
        )
        perm = perm_result.first()
        assert perm.expires_at is not None
        assert perm.expires_at > datetime.utcnow()

    async def test_revoke_user_permission(self, db_session, superuser, test_node_a):
        """
        Test revoking user permission

        Given: User has permission
        When: Revoking permission
        Then: Permission should be deleted
        """
        # Grant permission
        services = {"ssh": True, "rdp": False, "vnc": False, "http": False, "https": False}
        await PermissionService.grant_user_permission(
            db=db_session,
            user_id=superuser.id,
            node_id=test_node_a.id,
            granted_by_id=superuser.id,
            permission_level=PermissionLevel.CONNECT,
            services=services
        )

        # Revoke
        success = await PermissionService.revoke_user_permission(
            db=db_session,
            user_id=superuser.id,
            node_id=test_node_a.id
        )

        assert success is True

        # Verify deleted
        perm_result = await db_session.execute(
            select(user_node_permissions).where(
                user_node_permissions.c.user_id == superuser.id
            )
        )
        perm = perm_result.first()
        assert perm is None


@pytest.mark.asyncio
class TestAccessControl:
    """Test access control validation"""

    async def test_check_user_access_granted(self, db_session, superuser, test_node_a):
        """
        Test access check for user with permission

        Given: User has SSH permission
        When: Checking SSH access
        Then: Access should be granted
        """
        services = {"ssh": True, "rdp": False, "vnc": False, "http": False, "https": False}
        await PermissionService.grant_user_permission(
            db=db_session,
            user_id=superuser.id,
            node_id=test_node_a.id,
            granted_by_id=superuser.id,
            permission_level=PermissionLevel.CONNECT,
            services=services
        )

        allowed, reason = await PermissionService.check_user_access(
            db=db_session,
            user_id=superuser.id,
            node_id=test_node_a.id,
            service_type=ServiceType.SSH
        )

        assert allowed is True
        assert reason is None

    async def test_check_user_access_denied_no_permission(self, db_session, regular_user, test_node_a):
        """
        Test access check for user without permission

        Given: User has no permission
        When: Checking access
        Then: Access should be denied
        """
        allowed, reason = await PermissionService.check_user_access(
            db=db_session,
            user_id=regular_user.id,
            node_id=test_node_a.id,
            service_type=ServiceType.SSH
        )

        assert allowed is False
        assert "No permission" in reason

    async def test_check_user_access_denied_expired(self, db_session, superuser, test_node_a):
        """
        Test access check for expired permission

        Given: User has expired permission
        When: Checking access
        Then: Access should be denied with expiration reason
        """
        services = {"ssh": True, "rdp": False, "vnc": False, "http": False, "https": False}
        expired_time = datetime.utcnow() - timedelta(hours=1)

        await PermissionService.grant_user_permission(
            db=db_session,
            user_id=superuser.id,
            node_id=test_node_a.id,
            granted_by_id=superuser.id,
            permission_level=PermissionLevel.CONNECT,
            services=services,
            expires_at=expired_time
        )

        allowed, reason = await PermissionService.check_user_access(
            db=db_session,
            user_id=superuser.id,
            node_id=test_node_a.id,
            service_type=ServiceType.SSH
        )

        assert allowed is False
        assert "expired" in reason.lower()

    async def test_check_user_access_denied_wrong_service(self, db_session, superuser, test_node_a):
        """
        Test access check for wrong service type

        Given: User has SSH permission only
        When: Checking RDP access
        Then: Access should be denied
        """
        services = {"ssh": True, "rdp": False, "vnc": False, "http": False, "https": False}
        await PermissionService.grant_user_permission(
            db=db_session,
            user_id=superuser.id,
            node_id=test_node_a.id,
            granted_by_id=superuser.id,
            permission_level=PermissionLevel.CONNECT,
            services=services
        )

        allowed, reason = await PermissionService.check_user_access(
            db=db_session,
            user_id=superuser.id,
            node_id=test_node_a.id,
            service_type=ServiceType.RDP
        )

        assert allowed is False
        assert "not allowed" in reason.lower()

    async def test_check_user_access_ip_whitelist_allowed(self, db_session, superuser, test_node_a):
        """
        Test access check with IP whitelist - allowed IP

        Given: User has permission with IP whitelist
        When: Checking access from whitelisted IP
        Then: Access should be granted
        """
        services = {"ssh": True, "rdp": False, "vnc": False, "http": False, "https": False}
        allowed_ips = ["192.168.1.100", "10.0.0.50"]

        await PermissionService.grant_user_permission(
            db=db_session,
            user_id=superuser.id,
            node_id=test_node_a.id,
            granted_by_id=superuser.id,
            permission_level=PermissionLevel.CONNECT,
            services=services,
            ip_whitelist=allowed_ips
        )

        allowed, reason = await PermissionService.check_user_access(
            db=db_session,
            user_id=superuser.id,
            node_id=test_node_a.id,
            service_type=ServiceType.SSH,
            source_ip="192.168.1.100"
        )

        assert allowed is True
        assert reason is None

    async def test_check_user_access_ip_whitelist_denied(self, db_session, superuser, test_node_a):
        """
        Test access check with IP whitelist - denied IP

        Given: User has permission with IP whitelist
        When: Checking access from non-whitelisted IP
        Then: Access should be denied
        """
        services = {"ssh": True, "rdp": False, "vnc": False, "http": False, "https": False}
        allowed_ips = ["192.168.1.100"]

        await PermissionService.grant_user_permission(
            db=db_session,
            user_id=superuser.id,
            node_id=test_node_a.id,
            granted_by_id=superuser.id,
            permission_level=PermissionLevel.CONNECT,
            services=services,
            ip_whitelist=allowed_ips
        )

        allowed, reason = await PermissionService.check_user_access(
            db=db_session,
            user_id=superuser.id,
            node_id=test_node_a.id,
            service_type=ServiceType.SSH,
            source_ip="10.0.0.99"
        )

        assert allowed is False
        assert "not in whitelist" in reason.lower()


@pytest.mark.asyncio
class TestAccessLogging:
    """Test access logging functionality"""

    async def test_log_access_success(self, db_session, superuser, test_node_a):
        """
        Test logging successful access

        Given: User accesses node
        When: Logging access
        Then: AccessLog should be created with success=True
        """
        await PermissionService.log_access(
            db=db_session,
            user_id=superuser.id,
            node_id=test_node_a.id,
            service_type=ServiceType.SSH,
            action="connect",
            source_ip="192.168.1.100",
            success=True,
            session_id="test-session-123"
        )

        # Verify log
        result = await db_session.execute(select(AccessLog))
        logs = result.scalars().all()
        assert len(logs) == 1
        assert logs[0].user_id == superuser.id
        assert logs[0].success is True
        assert logs[0].action == "connect"

    async def test_log_access_denied(self, db_session, regular_user, test_node_a):
        """
        Test logging denied access

        Given: User denied access to node
        When: Logging denied access
        Then: AccessLog should be created with success=False and error message
        """
        await PermissionService.log_access(
            db=db_session,
            user_id=regular_user.id,
            node_id=test_node_a.id,
            service_type=ServiceType.SSH,
            action="connect",
            source_ip="10.0.0.50",
            success=False,
            error_message="No permission found"
        )

        result = await db_session.execute(select(AccessLog))
        logs = result.scalars().all()
        assert len(logs) == 1
        assert logs[0].success is False
        assert logs[0].error_message == "No permission found"


@pytest.mark.asyncio
class TestTunnelSessions:
    """Test tunnel session management"""

    async def test_create_tunnel_session(self, db_session, superuser, test_node_a):
        """
        Test creating active tunnel session

        Given: User with permission
        When: Creating tunnel session
        Then: TunnelSession should be created with status=active
        """
        session = await PermissionService.create_tunnel_session(
            db=db_session,
            user_id=superuser.id,
            node_id=test_node_a.id,
            service_type=ServiceType.SSH,
            tunnel_id="tunnel-ssh-12345",
            local_port=22,
            remote_port=2222,
            source_ip="192.168.1.100",
            metadata={"client": "openssh"}
        )

        assert session.tunnel_id == "tunnel-ssh-12345"
        assert session.status == "active"
        assert session.local_port == "22"
        assert session.started_at is not None

    async def test_get_active_tunnels_by_user(self, db_session, superuser, test_node_a, test_node_b):
        """
        Test getting active tunnels for specific user

        Given: Multiple active tunnels
        When: Getting tunnels for specific user
        Then: Only user's tunnels should be returned
        """
        # Create tunnels
        await PermissionService.create_tunnel_session(
            db=db_session,
            user_id=superuser.id,
            node_id=test_node_a.id,
            service_type=ServiceType.SSH,
            tunnel_id="tunnel-1",
            local_port=22,
            remote_port=2222,
            source_ip="192.168.1.100"
        )

        await PermissionService.create_tunnel_session(
            db=db_session,
            user_id=superuser.id,
            node_id=test_node_b.id,
            service_type=ServiceType.RDP,
            tunnel_id="tunnel-2",
            local_port=3389,
            remote_port=3389,
            source_ip="192.168.1.100"
        )

        tunnels = await PermissionService.get_active_tunnels(
            db=db_session,
            user_id=superuser.id
        )

        assert len(tunnels) == 2
        tunnel_ids = [t.tunnel_id for t in tunnels]
        assert "tunnel-1" in tunnel_ids
        assert "tunnel-2" in tunnel_ids

    async def test_close_tunnel_session(self, db_session, superuser, test_node_a):
        """
        Test closing tunnel session

        Given: Active tunnel session
        When: Closing session
        Then: Status should change to disconnected and ended_at set
        """
        session = await PermissionService.create_tunnel_session(
            db=db_session,
            user_id=superuser.id,
            node_id=test_node_a.id,
            service_type=ServiceType.SSH,
            tunnel_id="tunnel-to-close",
            local_port=22,
            remote_port=2222,
            source_ip="192.168.1.100"
        )

        success = await PermissionService.close_tunnel_session(
            db=db_session,
            tunnel_id="tunnel-to-close"
        )

        assert success is True

        # Verify status changed
        result = await db_session.execute(
            select(TunnelSession).where(TunnelSession.tunnel_id == "tunnel-to-close")
        )
        closed_session = result.scalar_one_or_none()
        assert closed_session.status == "disconnected"
        assert closed_session.ended_at is not None
