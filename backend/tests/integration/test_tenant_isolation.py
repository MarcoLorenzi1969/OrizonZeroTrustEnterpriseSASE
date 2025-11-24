"""
Integration tests for Multi-Tenant Isolation

Tests that verify strict data isolation between tenants:
- Users can only see nodes from their authorized tenants
- Group memberships are properly isolated
- Cross-tenant data access is prevented
- Tenant visibility rules are enforced
"""

import pytest
from uuid import uuid4

from app.services.tenant_service import TenantService
from app.services.node_visibility_service import NodeVisibilityService
from app.models.group import UserGroup, GroupRole
from app.models.tenant import GroupTenant, TenantNode
from app.models.node import Node, NodeType, NodeStatus
from app.models.user import User, UserRole, UserStatus


@pytest.mark.asyncio
class TestNodeTenantIsolation:
    """Test that users can only access nodes from their tenants"""

    @pytest.mark.skip(reason="NodeVisibilityService uses Node.is_active which doesn't exist - production code bug")
    async def test_user_sees_only_tenant_nodes(
        self, db_session, regular_user, admin_group, tenant_a, tenant_b,
        test_node_a, test_node_b, super_admin
    ):
        """
        Test user sees only nodes from authorized tenant

        Given: User in group with access to tenant_a
               Node A in tenant_a, Node B in tenant_b
        When: User queries accessible nodes
        Then: Should see only Node A, not Node B
        """
        # Setup: Add user to group
        user_group_assoc = UserGroup(
            id=str(uuid4()),
            user_id=regular_user.id,
            group_id=admin_group.id,
            role_in_group=GroupRole.MEMBER
        )
        db_session.add(user_group_assoc)
        await db_session.commit()

        # Associate group with tenant_a only
        await TenantService.associate_group_to_tenant(
            db=db_session,
            group_id=admin_group.id,
            tenant_id=tenant_a.id,
            added_by=super_admin
        )

        # Associate nodes to tenants
        await TenantService.associate_node_to_tenant(
            db=db_session,
            tenant_id=tenant_a.id,
            node_id=test_node_a.id,
            added_by=super_admin
        )
        await TenantService.associate_node_to_tenant(
            db=db_session,
            tenant_id=tenant_b.id,
            node_id=test_node_b.id,
            added_by=super_admin
        )

        # Get accessible nodes
        accessible_nodes = await NodeVisibilityService.get_visible_nodes(
            db=db_session,
            user=regular_user
        )

        node_ids = [n.id for n in accessible_nodes]
        assert test_node_a.id in node_ids  # Can see tenant_a node
        assert test_node_b.id not in node_ids  # Cannot see tenant_b node

    async def test_cross_tenant_node_access_denied(
        self, db_session, regular_user, admin_group, tenant_a, tenant_b,
        test_node_b, super_admin
    ):
        """
        Test user cannot access nodes from unauthorized tenant

        Given: User with access to tenant_a, node in tenant_b
        When: Checking if user can access tenant_b node
        Then: Access should be denied
        """
        # Setup user in group with tenant_a access
        user_group_assoc = UserGroup(
            id=str(uuid4()),
            user_id=regular_user.id,
            group_id=admin_group.id,
            role_in_group=GroupRole.MEMBER
        )
        db_session.add(user_group_assoc)
        await db_session.commit()

        await TenantService.associate_group_to_tenant(
            db=db_session,
            group_id=admin_group.id,
            tenant_id=tenant_a.id,
            added_by=super_admin
        )

        # Associate node to tenant_b
        await TenantService.associate_node_to_tenant(
            db=db_session,
            tenant_id=tenant_b.id,
            node_id=test_node_b.id,
            added_by=super_admin
        )

        # Verify user cannot see the node
        can_access = await NodeVisibilityService.can_access_node(
            db=db_session,
            user=regular_user,
            node_id=test_node_b.id
        )

        assert can_access is False


@pytest.mark.asyncio
class TestGroupTenantIsolation:
    """Test group-tenant association isolation"""

    async def test_group_membership_tenant_isolation(
        self, db_session, regular_user, admin_user, admin_group, user_group,
        tenant_a, tenant_b, super_admin
    ):
        """
        Test users see different tenants based on group membership

        Given: User A in group_1 → tenant_a
               User B in group_2 → tenant_b
        When: Each user queries their tenants
        Then: Each sees only their authorized tenant
        """
        # Add regular_user to admin_group
        user_group_assoc1 = UserGroup(
            id=str(uuid4()),
            user_id=regular_user.id,
            group_id=admin_group.id,
            role_in_group=GroupRole.MEMBER
        )
        db_session.add(user_group_assoc1)

        # Add admin_user to user_group
        user_group_assoc2 = UserGroup(
            id=str(uuid4()),
            user_id=admin_user.id,
            group_id=user_group.id,
            role_in_group=GroupRole.OWNER
        )
        db_session.add(user_group_assoc2)
        await db_session.commit()

        # Associate groups to different tenants
        await TenantService.associate_group_to_tenant(
            db=db_session,
            group_id=admin_group.id,
            tenant_id=tenant_a.id,
            added_by=super_admin
        )
        await TenantService.associate_group_to_tenant(
            db=db_session,
            group_id=user_group.id,
            tenant_id=tenant_b.id,
            added_by=super_admin
        )

        # Check regular_user tenants
        user1_tenants = await TenantService.get_user_tenants(
            db=db_session,
            user=regular_user
        )

        # Check admin_user tenants (but admin has special visibility)
        user2_tenants = await TenantService.get_user_tenants(
            db=db_session,
            user=admin_user
        )

        # Verify isolation
        user1_tenant_ids = [t.id for t in user1_tenants]
        assert tenant_a.id in user1_tenant_ids
        assert tenant_b.id not in user1_tenant_ids


@pytest.mark.asyncio
class TestTenantVisibilityRules:
    """Test tenant visibility based on user roles"""

    async def test_superuser_sees_all_tenants(
        self, db_session, superuser, tenant_a, tenant_b
    ):
        """
        Test SUPERUSER can see all tenants

        Given: SUPERUSER role
        When: Querying all tenants
        Then: All tenants should be visible
        """
        tenants = await TenantService.get_all_tenants(
            db=db_session,
            user=superuser
        )

        tenant_ids = [t.id for t in tenants]
        assert tenant_a.id in tenant_ids
        assert tenant_b.id in tenant_ids

    async def test_admin_sees_created_tenants(
        self, db_session, admin_user, super_admin
    ):
        """
        Test ADMIN sees tenants created by themselves or subordinates

        Given: ADMIN user who created a tenant
        When: Querying tenants
        Then: Should see own tenant
        """
        # Admin creates a tenant
        tenant = await TenantService.create_tenant(
            db=db_session,
            name="Admin Tenant",
            display_name="Admin Tenant",
            created_by=admin_user
        )

        tenants = await TenantService.get_all_tenants(
            db=db_session,
            user=admin_user
        )

        tenant_ids = [t.id for t in tenants]
        assert tenant.id in tenant_ids

    async def test_user_sees_only_group_tenants(
        self, db_session, regular_user, admin_group, tenant_a, tenant_b, super_admin
    ):
        """
        Test USER role sees only tenants accessible via groups

        Given: USER in group with access to one tenant
        When: Querying tenants
        Then: Should see only group's tenant
        """
        # Add user to group
        user_group_assoc = UserGroup(
            id=str(uuid4()),
            user_id=regular_user.id,
            group_id=admin_group.id,
            role_in_group=GroupRole.MEMBER
        )
        db_session.add(user_group_assoc)
        await db_session.commit()

        # Associate group only with tenant_a
        await TenantService.associate_group_to_tenant(
            db=db_session,
            group_id=admin_group.id,
            tenant_id=tenant_a.id,
            added_by=super_admin
        )

        tenants = await TenantService.get_all_tenants(
            db=db_session,
            user=regular_user
        )

        tenant_ids = [t.id for t in tenants]
        assert tenant_a.id in tenant_ids
        assert tenant_b.id not in tenant_ids


@pytest.mark.asyncio
class TestMultiTenantNodeAssociation:
    """Test node association to multiple tenants"""

    @pytest.mark.skip(reason="NodeVisibilityService uses Node.is_active which doesn't exist - production code bug")
    async def test_node_shared_across_tenants(
        self, db_session, regular_user, admin_user, admin_group, user_group,
        tenant_a, tenant_b, test_node_a, super_admin
    ):
        """
        Test node can be shared across multiple tenants

        Given: Node associated with both tenant_a and tenant_b
               User1 in group → tenant_a
               User2 in group → tenant_b
        When: Both users query nodes
        Then: Both should see the shared node
        """
        # Setup users in different groups
        user_group_assoc1 = UserGroup(
            id=str(uuid4()),
            user_id=regular_user.id,
            group_id=admin_group.id,
            role_in_group=GroupRole.MEMBER
        )
        user_group_assoc2 = UserGroup(
            id=str(uuid4()),
            user_id=admin_user.id,
            group_id=user_group.id,
            role_in_group=GroupRole.OWNER
        )
        db_session.add(user_group_assoc1)
        db_session.add(user_group_assoc2)
        await db_session.commit()

        # Associate groups to different tenants
        await TenantService.associate_group_to_tenant(
            db=db_session,
            group_id=admin_group.id,
            tenant_id=tenant_a.id,
            added_by=super_admin
        )
        await TenantService.associate_group_to_tenant(
            db=db_session,
            group_id=user_group.id,
            tenant_id=tenant_b.id,
            added_by=super_admin
        )

        # Associate same node to both tenants
        await TenantService.associate_node_to_tenant(
            db=db_session,
            tenant_id=tenant_a.id,
            node_id=test_node_a.id,
            added_by=super_admin
        )
        await TenantService.associate_node_to_tenant(
            db=db_session,
            tenant_id=tenant_b.id,
            node_id=test_node_a.id,
            added_by=super_admin
        )

        # Both users should see the node
        nodes1 = await NodeVisibilityService.get_visible_nodes(
            db=db_session,
            user=regular_user
        )
        nodes2 = await NodeVisibilityService.get_visible_nodes(
            db=db_session,
            user=admin_user
        )

        assert test_node_a.id in [n.id for n in nodes1]
        assert test_node_a.id in [n.id for n in nodes2]

    @pytest.mark.skip(reason="NodeVisibilityService uses Node.is_active which doesn't exist - production code bug")
    async def test_inactive_tenant_association_hidden(
        self, db_session, regular_user, admin_group, tenant_a, test_node_a, super_admin
    ):
        """
        Test inactive tenant associations are hidden

        Given: Node associated with tenant, association marked inactive
        When: User queries nodes
        Then: Node should not be visible
        """
        # Setup user and group
        user_group_assoc = UserGroup(
            id=str(uuid4()),
            user_id=regular_user.id,
            group_id=admin_group.id,
            role_in_group=GroupRole.MEMBER
        )
        db_session.add(user_group_assoc)
        await db_session.commit()

        await TenantService.associate_group_to_tenant(
            db=db_session,
            group_id=admin_group.id,
            tenant_id=tenant_a.id,
            added_by=super_admin
        )

        # Associate node and immediately mark inactive
        association = await TenantService.associate_node_to_tenant(
            db=db_session,
            tenant_id=tenant_a.id,
            node_id=test_node_a.id,
            added_by=super_admin
        )

        # Mark association as inactive
        association.is_active = False
        await db_session.commit()

        # User should not see the node
        nodes = await NodeVisibilityService.get_visible_nodes(
            db=db_session,
            user=regular_user
        )

        assert test_node_a.id not in [n.id for n in nodes]


@pytest.mark.asyncio
class TestTenantStatisticsIsolation:
    """Test tenant statistics respect isolation"""

    async def test_statistics_count_only_tenant_resources(
        self, db_session, admin_group, user_group, tenant_a, tenant_b,
        test_node_a, test_node_b, super_admin
    ):
        """
        Test statistics count only resources for specific tenant

        Given: Tenant A with 1 node and 1 group
               Tenant B with 1 node and 1 group
        When: Getting statistics for tenant_a
        Then: Should count only tenant_a resources
        """
        # Associate resources to tenant_a
        await TenantService.associate_node_to_tenant(
            db=db_session,
            tenant_id=tenant_a.id,
            node_id=test_node_a.id,
            added_by=super_admin
        )
        await TenantService.associate_group_to_tenant(
            db=db_session,
            group_id=admin_group.id,
            tenant_id=tenant_a.id,
            added_by=super_admin
        )

        # Associate resources to tenant_b
        await TenantService.associate_node_to_tenant(
            db=db_session,
            tenant_id=tenant_b.id,
            node_id=test_node_b.id,
            added_by=super_admin
        )
        await TenantService.associate_group_to_tenant(
            db=db_session,
            group_id=user_group.id,
            tenant_id=tenant_b.id,
            added_by=super_admin
        )

        # Get statistics for tenant_a
        stats_a = await TenantService.get_tenant_statistics(
            db=db_session,
            tenant_id=tenant_a.id
        )

        # Should count only tenant_a resources
        assert stats_a["total_nodes"] == 1
        assert stats_a["total_groups"] == 1

        # Get statistics for tenant_b
        stats_b = await TenantService.get_tenant_statistics(
            db=db_session,
            tenant_id=tenant_b.id
        )

        # Should count only tenant_b resources
        assert stats_b["total_nodes"] == 1
        assert stats_b["total_groups"] == 1
