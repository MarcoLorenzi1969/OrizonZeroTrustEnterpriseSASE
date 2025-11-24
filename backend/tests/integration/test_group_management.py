"""
Integration tests for Group Management

Tests the complete group lifecycle:
- Creating groups
- Adding/removing users
- Managing permissions
- Group deletion
"""

import pytest
from uuid import uuid4

from app.services.group_service import GroupService
from app.models.group import UserGroup, GroupRole
from app.models.user import User, UserRole


@pytest.mark.asyncio
class TestGroupCreation:
    """Test group creation and basic operations"""

    async def test_create_group(self, db_session, super_admin):
        """
        Test creating a new group

        Given: A super admin user
        When: Creating a new group
        Then: Group should be created with admin as owner
        """
        group = await GroupService.create_group(
            db=db_session,
            name="Test Development Team",
            description="Team for development work",
            settings={"max_nodes": 50},
            created_by=super_admin
        )

        assert group is not None
        assert group.name == "Test Development Team"
        assert group.description == "Team for development work"
        assert group.created_by == super_admin.id
        assert group.is_active is True
        
    async def test_get_group_by_id(self, db_session, super_admin):
        """Test retrieving group by ID"""
        # Create group
        group = await GroupService.create_group(
            db=db_session,
            name="QA Team",
            description="Quality Assurance",
            settings={},
            created_by=super_admin
        )

        # Retrieve group
        retrieved = await GroupService.get_group_by_id(db_session, group.id)

        assert retrieved is not None
        assert retrieved.id == group.id
        assert retrieved.name == group.name


@pytest.mark.asyncio
class TestGroupMembers:
    """Test adding/removing users from groups"""

    async def test_add_user_to_group(self, db_session, super_admin, regular_user, admin_group):
        """
        Test adding user to group

        Given: A group and a user
        When: Adding user to group as MEMBER
        Then: User should be in group with correct role
        """
        # Add user to group
        await GroupService.add_user_to_group(
            db=db_session,
            group_id=admin_group.id,
            user_id=regular_user.id,
            role_in_group=GroupRole.MEMBER,
            added_by=super_admin
        )

        # Verify membership
        role = await GroupService.get_user_role_in_group(
            db=db_session,
            user_id=regular_user.id,
            group_id=admin_group.id
        )

        assert role == GroupRole.MEMBER
        
    async def test_update_user_role_in_group(self, db_session, superuser, regular_user, admin_group):
        """Test updating user's role in group"""
        # Add user as MEMBER
        await GroupService.add_user_to_group(
            db=db_session,
            group_id=admin_group.id,
            user_id=regular_user.id,
            role_in_group=GroupRole.MEMBER,
            added_by=superuser
        )

        # Promote to ADMIN (using SUPERUSER)
        await GroupService.update_user_role_in_group(
            db=db_session,
            group_id=admin_group.id,
            user_id=regular_user.id,
            new_role=GroupRole.ADMIN,
            current_user=superuser
        )

        # Verify new role
        role = await GroupService.get_user_role_in_group(
            db=db_session,
            user_id=regular_user.id,
            group_id=admin_group.id
        )

        assert role == GroupRole.ADMIN
        
    async def test_remove_user_from_group(self, db_session, superuser, regular_user, admin_group):
        """Test removing user from group"""
        # Add user
        await GroupService.add_user_to_group(
            db=db_session,
            group_id=admin_group.id,
            user_id=regular_user.id,
            role_in_group=GroupRole.MEMBER,
            added_by=superuser
        )

        # Remove user (using SUPERUSER)
        success = await GroupService.remove_user_from_group(
            db=db_session,
            group_id=admin_group.id,
            user_id=regular_user.id,
            current_user=superuser
        )

        assert success is True

        # Verify removed
        role = await GroupService.get_user_role_in_group(
            db=db_session,
            user_id=regular_user.id,
            group_id=admin_group.id
        )

        assert role is None


@pytest.mark.asyncio
class TestGroupPermissions:
    """Test group-based permissions"""

    async def test_user_inherits_group_tenants(self, db_session, super_admin, regular_user, admin_group, tenant_a):
        """
        Test that user inherits tenant access through group

        Given: User in group, group has access to tenant
        When: Checking user's tenants
        Then: User should see tenant through group membership
        """
        from app.services.tenant_service import TenantService

        # Add user to group
        await GroupService.add_user_to_group(
            db=db_session,
            group_id=admin_group.id,
            user_id=regular_user.id,
            role_in_group=GroupRole.MEMBER,
            added_by=super_admin
        )

        # Associate group with tenant
        await TenantService.associate_group_to_tenant(
            db=db_session,
            group_id=admin_group.id,
            tenant_id=tenant_a.id,
            added_by=super_admin
        )

        # Check user can access tenant
        can_access = await TenantService.can_user_access_tenant(
            db=db_session,
            user=regular_user,
            tenant_id=tenant_a.id
        )

        assert can_access is True
        
    async def test_group_admin_can_add_members(self, db_session, admin_user, regular_user, user_group):
        """Test that group ADMIN can add members"""
        # Make admin_user an ADMIN of the group
        await GroupService.add_user_to_group(
            db=db_session,
            group_id=user_group.id,
            user_id=admin_user.id,
            role_in_group=GroupRole.ADMIN,
            added_by=admin_user
        )

        # Admin adds regular user
        await GroupService.add_user_to_group(
            db=db_session,
            group_id=user_group.id,
            user_id=regular_user.id,
            role_in_group=GroupRole.MEMBER,
            added_by=admin_user
        )

        # Verify membership
        role = await GroupService.get_user_role_in_group(
            db=db_session,
            user_id=regular_user.id,
            group_id=user_group.id
        )

        assert role == GroupRole.MEMBER


@pytest.mark.asyncio
class TestGroupDeletion:
    """Test group deletion"""

    async def test_delete_group(self, db_session, super_admin):
        """Test deleting a group"""
        # Create group
        group = await GroupService.create_group(
            db=db_session,
            name="Temporary Group",
            description="Will be deleted",
            settings={},
            created_by=super_admin
        )

        # Delete group
        success = await GroupService.delete_group(
            db=db_session,
            group_id=group.id,
            current_user=super_admin
        )

        assert success is True

        # Verify deleted (soft delete - is_active = False)
        deleted_group = await GroupService.get_group_by_id(db_session, group.id)
        assert deleted_group is None or deleted_group.is_active is False
