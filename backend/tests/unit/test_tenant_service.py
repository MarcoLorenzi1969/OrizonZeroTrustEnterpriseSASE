"""
Unit tests for Tenant Service

Tests for app.services.tenant_service covering:
- Tenant creation and slug generation
- Tenant retrieval (by ID, by slug, all tenants)
- Group-Tenant associations
- Node-Tenant associations
- User access control to tenants
- Tenant statistics
"""

import pytest
from sqlalchemy import select

from app.services.tenant_service import TenantService
from app.models.tenant import Tenant, GroupTenant, TenantNode
from app.models.user import User, UserRole
from app.models.group import Group
from app.models.node import Node, NodeStatus


@pytest.mark.asyncio
class TestTenantCreation:
    """Test tenant creation and slug generation"""

    async def test_create_tenant_basic(self, db_session, super_admin):
        """
        Test creating basic tenant

        Given: Valid tenant data
        When: Creating tenant
        Then: Tenant should be created with auto-generated slug
        """
        tenant = await TenantService.create_tenant(
            db=db_session,
            name="Acme Corporation",
            display_name="ACME Corp",
            created_by=super_admin,
            description="Test tenant"
        )

        assert tenant.id is not None
        assert tenant.name == "Acme Corporation"
        assert tenant.display_name == "ACME Corp"
        assert tenant.slug == "acme-corporation"
        assert tenant.created_by_id == super_admin.id
        assert tenant.is_active is True

    async def test_create_tenant_with_company_info(self, db_session, super_admin):
        """
        Test creating tenant with company information

        Given: Tenant with company_info and quota
        When: Creating tenant
        Then: Data should be stored correctly
        """
        company_info = {
            "legal_name": "Acme Corp Ltd",
            "vat_number": "IT12345678901",
            "address": "123 Main St"
        }
        quota = {
            "max_nodes": 50,
            "max_users": 100
        }

        tenant = await TenantService.create_tenant(
            db=db_session,
            name="Acme",
            display_name="ACME",
            created_by=super_admin,
            company_info=company_info,
            quota=quota
        )

        assert tenant.company_info == company_info
        assert tenant.quota == quota

    async def test_slug_generation_special_chars(self, db_session, super_admin):
        """
        Test slug generation with special characters

        Given: Tenant name with special characters
        When: Creating tenant
        Then: Slug should be sanitized (lowercase, no special chars)
        """
        tenant = await TenantService.create_tenant(
            db=db_session,
            name="Test! Company @#$ 123",
            display_name="Test Company",
            created_by=super_admin
        )

        assert tenant.slug == "test-company-123"

    async def test_slug_collision_handling(self, db_session, super_admin):
        """
        Test slug collision handling with numeric suffix

        Given: Two tenants with similar names generating same slug
        When: Creating second tenant
        Then: Second slug should have numeric suffix
        """
        # Create first tenant
        tenant1 = await TenantService.create_tenant(
            db=db_session,
            name="Test Company",
            display_name="Test Company 1",
            created_by=super_admin
        )

        # Create second with different name but same slug pattern
        tenant2 = await TenantService.create_tenant(
            db=db_session,
            name="Test-Company",  # Different name, same slug after sanitization
            display_name="Test Company 2",
            created_by=super_admin
        )

        assert tenant1.slug == "test-company"
        assert tenant2.slug == "test-company-1"


@pytest.mark.asyncio
class TestTenantRetrieval:
    """Test tenant retrieval methods"""

    async def test_get_tenant_by_id(self, db_session, tenant_a):
        """
        Test retrieving tenant by ID

        Given: Existing tenant
        When: Getting by ID
        Then: Correct tenant should be returned
        """
        tenant = await TenantService.get_tenant_by_id(
            db=db_session,
            tenant_id=tenant_a.id
        )

        assert tenant is not None
        assert tenant.id == tenant_a.id
        assert tenant.name == tenant_a.name

    async def test_get_tenant_by_id_not_found(self, db_session):
        """
        Test getting non-existent tenant

        Given: Invalid tenant ID
        When: Getting tenant
        Then: None should be returned
        """
        tenant = await TenantService.get_tenant_by_id(
            db=db_session,
            tenant_id="non-existent-id"
        )

        assert tenant is None

    async def test_get_tenant_by_slug(self, db_session, tenant_a):
        """
        Test retrieving tenant by slug

        Given: Existing tenant with slug
        When: Getting by slug
        Then: Correct tenant should be returned
        """
        tenant = await TenantService.get_tenant_by_slug(
            db=db_session,
            slug=tenant_a.slug
        )

        assert tenant is not None
        assert tenant.id == tenant_a.id
        assert tenant.slug == tenant_a.slug

    async def test_get_all_tenants_superuser(self, db_session, superuser, tenant_a, tenant_b):
        """
        Test SUPERUSER can see all tenants

        Given: SUPERUSER role
        When: Getting all tenants
        Then: All tenants should be visible
        """
        tenants = await TenantService.get_all_tenants(
            db=db_session,
            user=superuser
        )

        assert len(tenants) >= 2
        tenant_ids = [t.id for t in tenants]
        assert tenant_a.id in tenant_ids
        assert tenant_b.id in tenant_ids

    async def test_get_all_tenants_user_with_access(
        self, db_session, regular_user, tenant_a, admin_group, super_admin
    ):
        """
        Test USER sees only tenants accessible via groups

        Given: User in group associated with tenant
        When: Getting all tenants
        Then: Only accessible tenant should be visible
        """
        from app.models.group import UserGroup, GroupRole
        from uuid import uuid4

        # Add user to group
        user_group_assoc = UserGroup(
            id=str(uuid4()),
            user_id=regular_user.id,
            group_id=admin_group.id,
            role_in_group=GroupRole.MEMBER
        )
        db_session.add(user_group_assoc)
        await db_session.commit()

        # Associate group to tenant
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

        assert len(tenants) >= 1
        assert tenant_a.id in [t.id for t in tenants]

    async def test_get_all_tenants_pagination(self, db_session, superuser):
        """
        Test tenant list pagination

        Given: Multiple tenants
        When: Getting with skip/limit
        Then: Correct subset should be returned
        """
        # Create 5 tenants
        for i in range(5):
            await TenantService.create_tenant(
                db=db_session,
                name=f"Tenant {i}",
                display_name=f"Tenant {i}",
                created_by=superuser
            )

        # Get first 2
        tenants_page1 = await TenantService.get_all_tenants(
            db=db_session,
            user=superuser,
            skip=0,
            limit=2
        )

        assert len(tenants_page1) == 2


@pytest.mark.asyncio
class TestGroupTenantAssociation:
    """Test group-tenant association"""

    async def test_associate_group_to_tenant(
        self, db_session, admin_group, tenant_a, super_admin
    ):
        """
        Test associating group to tenant

        Given: Valid group and tenant
        When: Creating association
        Then: GroupTenant should be created
        """
        association = await TenantService.associate_group_to_tenant(
            db=db_session,
            group_id=admin_group.id,
            tenant_id=tenant_a.id,
            added_by=super_admin
        )

        assert association.group_id == admin_group.id
        assert association.tenant_id == tenant_a.id
        assert association.is_active is True

    async def test_associate_group_duplicate_fails(
        self, db_session, admin_group, tenant_a, super_admin
    ):
        """
        Test duplicate group-tenant association fails

        Given: Existing association
        When: Creating duplicate
        Then: ValueError should be raised
        """
        # Create first association
        await TenantService.associate_group_to_tenant(
            db=db_session,
            group_id=admin_group.id,
            tenant_id=tenant_a.id,
            added_by=super_admin
        )

        # Try duplicate
        with pytest.raises(ValueError, match="già esistente"):
            await TenantService.associate_group_to_tenant(
                db=db_session,
                group_id=admin_group.id,
                tenant_id=tenant_a.id,
                added_by=super_admin
            )

    async def test_get_tenant_groups(
        self, db_session, admin_group, user_group, tenant_a, super_admin
    ):
        """
        Test getting all groups associated with tenant

        Given: Tenant with multiple group associations
        When: Getting tenant groups
        Then: All associations should be returned
        """
        # Associate two groups
        await TenantService.associate_group_to_tenant(
            db=db_session,
            group_id=admin_group.id,
            tenant_id=tenant_a.id,
            added_by=super_admin
        )
        await TenantService.associate_group_to_tenant(
            db=db_session,
            group_id=user_group.id,
            tenant_id=tenant_a.id,
            added_by=super_admin
        )

        groups = await TenantService.get_tenant_groups(
            db=db_session,
            tenant_id=tenant_a.id
        )

        assert len(groups) == 2
        group_ids = [g.group_id for g in groups]
        assert admin_group.id in group_ids
        assert user_group.id in group_ids


@pytest.mark.asyncio
class TestNodeTenantAssociation:
    """Test node-tenant association"""

    async def test_associate_node_to_tenant(
        self, db_session, test_node_a, tenant_a, super_admin
    ):
        """
        Test associating node to tenant

        Given: Valid node and tenant
        When: Creating association
        Then: TenantNode should be created
        """
        node_config = {"access_level": "full"}

        association = await TenantService.associate_node_to_tenant(
            db=db_session,
            tenant_id=tenant_a.id,
            node_id=test_node_a.id,
            added_by=super_admin,
            node_config=node_config
        )

        assert association.tenant_id == tenant_a.id
        assert association.node_id == test_node_a.id
        assert association.node_config == node_config
        assert association.is_active is True

    async def test_associate_node_duplicate_fails(
        self, db_session, test_node_a, tenant_a, super_admin
    ):
        """
        Test duplicate node-tenant association fails

        Given: Existing association
        When: Creating duplicate
        Then: ValueError should be raised
        """
        # Create first association
        await TenantService.associate_node_to_tenant(
            db=db_session,
            tenant_id=tenant_a.id,
            node_id=test_node_a.id,
            added_by=super_admin
        )

        # Try duplicate
        with pytest.raises(ValueError, match="già esistente"):
            await TenantService.associate_node_to_tenant(
                db=db_session,
                tenant_id=tenant_a.id,
                node_id=test_node_a.id,
                added_by=super_admin
            )

    async def test_get_tenant_nodes(
        self, db_session, test_node_a, test_node_b, tenant_a, super_admin
    ):
        """
        Test getting all nodes associated with tenant

        Given: Tenant with multiple node associations
        When: Getting tenant nodes
        Then: All associations should be returned
        """
        # Associate two nodes
        await TenantService.associate_node_to_tenant(
            db=db_session,
            tenant_id=tenant_a.id,
            node_id=test_node_a.id,
            added_by=super_admin
        )
        await TenantService.associate_node_to_tenant(
            db=db_session,
            tenant_id=tenant_a.id,
            node_id=test_node_b.id,
            added_by=super_admin
        )

        nodes = await TenantService.get_tenant_nodes(
            db=db_session,
            tenant_id=tenant_a.id
        )

        assert len(nodes) == 2
        node_ids = [n.node_id for n in nodes]
        assert test_node_a.id in node_ids
        assert test_node_b.id in node_ids


@pytest.mark.asyncio
class TestUserAccessControl:
    """Test user access control to tenants"""

    async def test_can_user_access_tenant_superuser(
        self, db_session, superuser, tenant_a
    ):
        """
        Test SUPERUSER can access any tenant

        Given: SUPERUSER role
        When: Checking access to any tenant
        Then: Access should be granted
        """
        can_access = await TenantService.can_user_access_tenant(
            db=db_session,
            user=superuser,
            tenant_id=tenant_a.id
        )

        assert can_access is True

    async def test_can_user_access_tenant_via_group(
        self, db_session, regular_user, admin_group, tenant_a, super_admin
    ):
        """
        Test USER can access tenant via group membership

        Given: User in group associated with tenant
        When: Checking access
        Then: Access should be granted
        """
        from app.models.group import UserGroup, GroupRole
        from uuid import uuid4

        # Add user to group
        user_group_assoc = UserGroup(
            id=str(uuid4()),
            user_id=regular_user.id,
            group_id=admin_group.id,
            role_in_group=GroupRole.MEMBER
        )
        db_session.add(user_group_assoc)
        await db_session.commit()

        # Associate group to tenant
        await TenantService.associate_group_to_tenant(
            db=db_session,
            group_id=admin_group.id,
            tenant_id=tenant_a.id,
            added_by=super_admin
        )

        can_access = await TenantService.can_user_access_tenant(
            db=db_session,
            user=regular_user,
            tenant_id=tenant_a.id
        )

        assert can_access is True

    async def test_can_user_access_tenant_denied(
        self, db_session, regular_user, tenant_a
    ):
        """
        Test USER cannot access tenant without group membership

        Given: User NOT in any group associated with tenant
        When: Checking access
        Then: Access should be denied
        """
        can_access = await TenantService.can_user_access_tenant(
            db=db_session,
            user=regular_user,
            tenant_id=tenant_a.id
        )

        assert can_access is False

    async def test_get_user_tenants(
        self, db_session, regular_user, admin_group, tenant_a, tenant_b, super_admin
    ):
        """
        Test getting all tenants accessible to user

        Given: User in group with access to specific tenant
        When: Getting user tenants
        Then: Only accessible tenants should be returned
        """
        from app.models.group import UserGroup, GroupRole
        from uuid import uuid4

        # Add user to group
        user_group_assoc = UserGroup(
            id=str(uuid4()),
            user_id=regular_user.id,
            group_id=admin_group.id,
            role_in_group=GroupRole.MEMBER
        )
        db_session.add(user_group_assoc)
        await db_session.commit()

        # Associate group to tenant_a only
        await TenantService.associate_group_to_tenant(
            db=db_session,
            group_id=admin_group.id,
            tenant_id=tenant_a.id,
            added_by=super_admin
        )

        tenants = await TenantService.get_user_tenants(
            db=db_session,
            user=regular_user
        )

        assert len(tenants) == 1
        assert tenants[0].id == tenant_a.id


@pytest.mark.asyncio
class TestTenantStatistics:
    """Test tenant statistics"""

    async def test_get_tenant_statistics(
        self, db_session, tenant_a, test_node_a, admin_group, super_admin
    ):
        """
        Test getting tenant statistics

        Given: Tenant with nodes and groups
        When: Getting statistics
        Then: Correct counts should be returned
        """
        # Associate node
        await TenantService.associate_node_to_tenant(
            db=db_session,
            tenant_id=tenant_a.id,
            node_id=test_node_a.id,
            added_by=super_admin
        )

        # Associate group
        await TenantService.associate_group_to_tenant(
            db=db_session,
            group_id=admin_group.id,
            tenant_id=tenant_a.id,
            added_by=super_admin
        )

        stats = await TenantService.get_tenant_statistics(
            db=db_session,
            tenant_id=tenant_a.id
        )

        assert stats["tenant_id"] == tenant_a.id
        assert stats["total_nodes"] >= 1
        assert stats["total_groups"] >= 1
        assert "quota" in stats

    async def test_get_tenant_statistics_empty(
        self, db_session, tenant_b
    ):
        """
        Test getting statistics for tenant with no associations

        Given: Tenant with no nodes/groups
        When: Getting statistics
        Then: All counts should be 0
        """
        stats = await TenantService.get_tenant_statistics(
            db=db_session,
            tenant_id=tenant_b.id
        )

        assert stats["total_nodes"] == 0
        assert stats["total_groups"] == 0
