"""
Unit tests for ACL Service
"""

import pytest
from datetime import datetime

from app.services.acl_service import acl_service
from app.models.access_rule import AccessRule, RuleAction, RuleProtocol


@pytest.mark.asyncio
class TestACLService:
    """Test ACL service functionality"""

    async def test_create_acl_rule(self, db_session):
        """Test creating ACL rule"""
        rule = await acl_service.create_rule(
            db=db_session,
            source_node="node-001",
            dest_node="node-002",
            protocol="tcp",
            port=22,
            action="allow",
            priority=50,
            created_by="admin@orizon.com",
            description="Test rule"
        )

        assert rule is not None
        assert rule.source_node_id == "node-001"
        assert rule.dest_node_id == "node-002"
        assert rule.protocol == RuleProtocol.TCP
        assert rule.port == 22
        assert rule.action == RuleAction.ALLOW
        assert rule.priority == 50
        assert rule.is_active is True

    async def test_check_access_allow(self, db_session):
        """Test access check with ALLOW rule"""
        # Create allow rule
        await acl_service.create_rule(
            db=db_session,
            source_node="node-001",
            dest_node="node-002",
            protocol="tcp",
            port=22,
            action="allow",
            priority=50,
            created_by="admin@orizon.com"
        )

        # Check access
        is_allowed = await acl_service.check_access(
            db=db_session,
            source="node-001",
            dest="node-002",
            protocol="tcp",
            port=22
        )

        assert is_allowed is True

    async def test_check_access_deny(self, db_session):
        """Test access check with DENY rule"""
        # Create deny rule
        await acl_service.create_rule(
            db=db_session,
            source_node="node-001",
            dest_node="node-002",
            protocol="tcp",
            port=22,
            action="deny",
            priority=50,
            created_by="admin@orizon.com"
        )

        # Check access
        is_allowed = await acl_service.check_access(
            db=db_session,
            source="node-001",
            dest="node-002",
            protocol="tcp",
            port=22
        )

        assert is_allowed is False

    async def test_check_access_default_deny(self, db_session):
        """Test that default policy is DENY (Zero Trust)"""
        # Check access without any rules
        is_allowed = await acl_service.check_access(
            db=db_session,
            source="node-001",
            dest="node-002",
            protocol="tcp",
            port=22
        )

        assert is_allowed is False

    async def test_rule_priority(self, db_session):
        """Test that rules are applied by priority"""
        # Create high priority deny rule
        await acl_service.create_rule(
            db=db_session,
            source_node="node-001",
            dest_node="node-002",
            protocol="tcp",
            port=22,
            action="deny",
            priority=10,  # High priority
            created_by="admin@orizon.com"
        )

        # Create low priority allow rule
        await acl_service.create_rule(
            db=db_session,
            source_node="node-001",
            dest_node="node-002",
            protocol="tcp",
            port=22,
            action="allow",
            priority=50,  # Lower priority
            created_by="admin@orizon.com"
        )

        # Check access - should be denied by high priority rule
        is_allowed = await acl_service.check_access(
            db=db_session,
            source="node-001",
            dest="node-002",
            protocol="tcp",
            port=22
        )

        assert is_allowed is False

    async def test_wildcard_rules(self, db_session):
        """Test wildcard rules (* for any node)"""
        # Create rule allowing any node to any node
        await acl_service.create_rule(
            db=db_session,
            source_node="*",
            dest_node="*",
            protocol="tcp",
            port=443,
            action="allow",
            priority=50,
            created_by="admin@orizon.com"
        )

        # Check access from any node
        is_allowed = await acl_service.check_access(
            db=db_session,
            source="node-001",
            dest="node-002",
            protocol="tcp",
            port=443
        )

        assert is_allowed is True

    async def test_delete_rule(self, db_session):
        """Test deleting ACL rule"""
        # Create rule
        rule = await acl_service.create_rule(
            db=db_session,
            source_node="node-001",
            dest_node="node-002",
            protocol="tcp",
            port=22,
            action="allow",
            priority=50,
            created_by="admin@orizon.com"
        )

        # Delete rule
        success = await acl_service.delete_rule(db_session, rule.id)

        assert success is True

        # Verify access is denied after rule deletion
        is_allowed = await acl_service.check_access(
            db=db_session,
            source="node-001",
            dest="node-002",
            protocol="tcp",
            port=22
        )

        assert is_allowed is False

    async def test_enable_disable_rule(self, db_session):
        """Test enabling/disabling ACL rule"""
        # Create rule
        rule = await acl_service.create_rule(
            db=db_session,
            source_node="node-001",
            dest_node="node-002",
            protocol="tcp",
            port=22,
            action="allow",
            priority=50,
            created_by="admin@orizon.com"
        )

        # Disable rule
        await acl_service.disable_rule(db_session, rule.id)

        # Check access - should be denied
        is_allowed = await acl_service.check_access(
            db=db_session,
            source="node-001",
            dest="node-002",
            protocol="tcp",
            port=22
        )

        assert is_allowed is False

        # Re-enable rule
        await acl_service.enable_rule(db_session, rule.id)

        # Check access - should be allowed
        is_allowed = await acl_service.check_access(
            db=db_session,
            source="node-001",
            dest="node-002",
            protocol="tcp",
            port=22
        )

        assert is_allowed is True
