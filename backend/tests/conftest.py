"""
Orizon Zero Trust Connect - Enhanced PyTest Configuration
For: Marco @ Syneto/Orizon

Comprehensive test fixtures for:
- Database sessions with in-memory SQLite
- User factories (all roles: SUPERUSER, SUPER_ADMIN, ADMIN, USER)
- Tenant factories
- Group factories
- Token factories (valid, expired, invalid)
- Association factories (group-tenant, tenant-node)
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from uuid import uuid4

from app.core.database import Base, get_db
from app.core.config import settings
from app.auth.security import get_password_hash, create_access_token
from app.models.user import User, UserRole, UserStatus
from app.models.tenant import Tenant, GroupTenant, TenantNode
from app.models.group import Group, UserGroup, GroupRole
from app.models.node import Node
# Skip app import for unit tests - avoid loading all API endpoints and their dependencies
# from app.main import app


# Test database URL (in-memory SQLite for speed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Standard test password (hashed)
TEST_PASSWORD = "TestPassword123!"


# ============================================================================
# CORE FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create test database session

    Each test gets a fresh database
    """
    # Create async engine
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    TestingSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with TestingSessionLocal() as session:
        yield session

    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
def override_get_db(db_session: AsyncSession):
    """Override get_db dependency for testing"""
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


# ============================================================================
# USER FACTORIES (All Roles)
# ============================================================================

@pytest.fixture
async def superuser(db_session: AsyncSession) -> User:
    """
    Create SUPERUSER for tests

    Full system access, sees all tenants
    """
    user = User(
        id=str(uuid4()),
        email="superuser@orizon.test",
        username="superuser",
        hashed_password=get_password_hash(TEST_PASSWORD),
        full_name="Super User",
        role=UserRole.SUPERUSER,
        status=UserStatus.ACTIVE,
        is_active=True,
        is_email_verified=True,
        can_create_users=True,
        can_manage_nodes=True,
        can_manage_tunnels=True,
        created_at=datetime.utcnow()
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def super_admin(db_session: AsyncSession, superuser: User) -> User:
    """
    Create SUPER_ADMIN for tests

    Manages own tenants and subordinate users
    Created by SUPERUSER
    """
    user = User(
        id=str(uuid4()),
        email="super_admin@orizon.test",
        username="super_admin",
        hashed_password=get_password_hash(TEST_PASSWORD),
        full_name="Super Admin User",
        role=UserRole.SUPER_ADMIN,
        status=UserStatus.ACTIVE,
        is_active=True,
        is_email_verified=True,
        can_create_users=True,
        can_manage_nodes=True,
        can_manage_tunnels=True,
        created_by_id=superuser.id,
        created_at=datetime.utcnow()
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def admin_user(db_session: AsyncSession, super_admin: User) -> User:
    """
    Create ADMIN for tests

    Manages groups and tenant associations
    Created by SUPER_ADMIN
    """
    user = User(
        id=str(uuid4()),
        email="admin@orizon.test",
        username="admin",
        hashed_password=get_password_hash(TEST_PASSWORD),
        full_name="Admin User",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        is_active=True,
        is_email_verified=True,
        can_create_users=False,
        can_manage_nodes=True,
        can_manage_tunnels=True,
        created_by_id=super_admin.id,
        created_at=datetime.utcnow()
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def regular_user(db_session: AsyncSession, admin_user: User) -> User:
    """
    Create regular USER for tests

    Read-only access to assigned tenants
    Created by ADMIN
    """
    user = User(
        id=str(uuid4()),
        email="user@orizon.test",
        username="regular_user",
        hashed_password=get_password_hash(TEST_PASSWORD),
        full_name="Regular User",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        is_active=True,
        is_email_verified=True,
        can_create_users=False,
        can_manage_nodes=False,
        can_manage_tunnels=True,
        created_by_id=admin_user.id,
        created_at=datetime.utcnow()
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def inactive_user(db_session: AsyncSession, admin_user: User) -> User:
    """Create INACTIVE user for negative testing"""
    user = User(
        id=str(uuid4()),
        email="inactive@orizon.test",
        username="inactive_user",
        hashed_password=get_password_hash(TEST_PASSWORD),
        full_name="Inactive User",
        role=UserRole.USER,
        status=UserStatus.INACTIVE,
        is_active=False,
        created_by_id=admin_user.id,
        created_at=datetime.utcnow()
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# ============================================================================
# TENANT FACTORIES
# ============================================================================

@pytest.fixture
async def tenant_a(db_session: AsyncSession, super_admin: User) -> Tenant:
    """
    Tenant A for isolation testing

    Used to verify cross-tenant isolation
    """
    tenant = Tenant(
        id=str(uuid4()),
        name="tenant-a",
        display_name="Tenant A Corporation",
        description="First test tenant for isolation",
        slug="tenant-a",
        company_info={
            "legal_name": "Tenant A Corp",
            "vat_number": "IT11111111111",
            "address": "Via Roma 1, Milano",
            "contact_email": "admin@tenant-a.test"
        },
        settings={
            "max_nodes": 10,
            "max_users": 50,
            "require_mfa": False
        },
        quota={
            "nodes_limit": 10,
            "users_limit": 50,
            "bandwidth_gb_month": 1000
        },
        created_by_id=super_admin.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest.fixture
async def tenant_b(db_session: AsyncSession, super_admin: User) -> Tenant:
    """
    Tenant B for isolation testing

    Used to verify cross-tenant isolation
    """
    tenant = Tenant(
        id=str(uuid4()),
        name="tenant-b",
        display_name="Tenant B Limited",
        description="Second test tenant for isolation",
        slug="tenant-b",
        company_info={
            "legal_name": "Tenant B Ltd",
            "vat_number": "IT22222222222",
            "address": "Corso Italia 2, Roma",
            "contact_email": "admin@tenant-b.test"
        },
        settings={
            "max_nodes": 5,
            "max_users": 20,
            "require_mfa": True
        },
        quota={
            "nodes_limit": 5,
            "users_limit": 20,
            "bandwidth_gb_month": 500
        },
        created_by_id=super_admin.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest.fixture
async def inactive_tenant(db_session: AsyncSession, super_admin: User) -> Tenant:
    """Inactive tenant for negative testing"""
    tenant = Tenant(
        id=str(uuid4()),
        name="tenant-inactive",
        display_name="Inactive Tenant",
        slug="tenant-inactive",
        created_by_id=super_admin.id,
        is_active=False,
        created_at=datetime.utcnow()
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


# ============================================================================
# GROUP FACTORIES
# ============================================================================

@pytest.fixture
async def admin_group(db_session: AsyncSession, admin_user: User) -> Group:
    """Admin group created by ADMIN user"""
    group = Group(
        id=str(uuid4()),
        name="admin-group",
        description="Admin group for testing",
        settings={
            "allow_terminal": True,
            "allow_rdp": True,
            "allow_vnc": True,
            "max_concurrent_sessions": 10
        },
        created_by=admin_user.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(group)
    await db_session.commit()
    await db_session.refresh(group)
    return group


@pytest.fixture
async def user_group(db_session: AsyncSession, admin_user: User) -> Group:
    """Regular user group"""
    group = Group(
        id=str(uuid4()),
        name="user-group",
        description="User group for testing",
        settings={
            "allow_terminal": True,
            "allow_rdp": False,
            "allow_vnc": False,
            "max_concurrent_sessions": 5
        },
        created_by=admin_user.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(group)
    await db_session.commit()
    await db_session.refresh(group)
    return group


@pytest.fixture
async def inactive_group(db_session: AsyncSession, admin_user: User) -> Group:
    """Inactive group for negative testing"""
    group = Group(
        id=str(uuid4()),
        name="inactive-group",
        description="Inactive group",
        created_by=admin_user.id,
        is_active=False,
        created_at=datetime.utcnow()
    )
    db_session.add(group)
    await db_session.commit()
    await db_session.refresh(group)
    return group


# ============================================================================
# USER-GROUP ASSOCIATIONS
# ============================================================================

@pytest.fixture
async def admin_in_admin_group(
    db_session: AsyncSession,
    admin_user: User,
    admin_group: Group
) -> UserGroup:
    """Associate admin_user with admin_group as OWNER"""
    user_group = UserGroup(
        id=str(uuid4()),
        user_id=admin_user.id,
        group_id=admin_group.id,
        role_in_group=GroupRole.OWNER,
        permissions={},
        added_by=admin_user.id,
        added_at=datetime.utcnow()
    )
    db_session.add(user_group)
    await db_session.commit()
    await db_session.refresh(user_group)
    return user_group


@pytest.fixture
async def user_in_user_group(
    db_session: AsyncSession,
    regular_user: User,
    user_group: Group,
    admin_user: User
) -> UserGroup:
    """Associate regular_user with user_group as MEMBER"""
    user_group_assoc = UserGroup(
        id=str(uuid4()),
        user_id=regular_user.id,
        group_id=user_group.id,
        role_in_group=GroupRole.MEMBER,
        permissions={},
        added_by=admin_user.id,
        added_at=datetime.utcnow()
    )
    db_session.add(user_group_assoc)
    await db_session.commit()
    await db_session.refresh(user_group_assoc)
    return user_group_assoc


# ============================================================================
# NODE FACTORIES
# ============================================================================

@pytest.fixture
async def test_node_a(db_session: AsyncSession, admin_user: User) -> Node:
    """Test node A for tenant associations"""
    from app.models.node import Node, NodeType, NodeStatus

    node = Node(
        id=str(uuid4()),
        name="test-node-a",
        hostname="node-a.orizon.test",
        node_type=NodeType.LINUX,
        status=NodeStatus.ONLINE,
        public_ip="10.0.1.10",
        private_ip="192.168.1.10",
        owner_id=admin_user.id,
        created_at=datetime.utcnow()
    )
    db_session.add(node)
    await db_session.commit()
    await db_session.refresh(node)
    return node


@pytest.fixture
async def test_node_b(db_session: AsyncSession, admin_user: User) -> Node:
    """Test node B for tenant associations"""
    from app.models.node import Node, NodeType, NodeStatus

    node = Node(
        id=str(uuid4()),
        name="test-node-b",
        hostname="node-b.orizon.test",
        node_type=NodeType.LINUX,
        status=NodeStatus.ONLINE,
        public_ip="10.0.1.20",
        private_ip="192.168.1.20",
        owner_id=admin_user.id,
        created_at=datetime.utcnow()
    )
    db_session.add(node)
    await db_session.commit()
    await db_session.refresh(node)
    return node


# ============================================================================
# ASSOCIATION FACTORIES
# ============================================================================

@pytest.fixture
async def group_tenant_association(
    db_session: AsyncSession,
    admin_group: Group,
    tenant_a: Tenant,
    admin_user: User
) -> GroupTenant:
    """Associate admin_group with tenant_a"""
    association = GroupTenant(
        id=str(uuid4()),
        group_id=admin_group.id,
        tenant_id=tenant_a.id,
        permissions={
            "can_manage_nodes": True,
            "can_view_metrics": True,
            "can_modify_settings": False
        },
        added_by_id=admin_user.id,
        added_at=datetime.utcnow(),
        is_active=True
    )
    db_session.add(association)
    await db_session.commit()
    await db_session.refresh(association)
    return association


@pytest.fixture
async def tenant_node_association(
    db_session: AsyncSession,
    tenant_a: Tenant,
    test_node_a: Node,
    admin_user: User
) -> TenantNode:
    """Associate tenant_a with test_node_a"""
    association = TenantNode(
        id=str(uuid4()),
        tenant_id=tenant_a.id,
        node_id=test_node_a.id,
        node_config={
            "priority": 1,
            "max_tunnels": 100,
            "allowed_ports": [22, 80, 443, 3389],
            "custom_routing": {"default_gateway": "10.0.0.1"}
        },
        added_by_id=admin_user.id,
        added_at=datetime.utcnow(),
        is_active=True
    )
    db_session.add(association)
    await db_session.commit()
    await db_session.refresh(association)
    return association


# ============================================================================
# TOKEN FACTORIES
# ============================================================================

@pytest.fixture
def valid_token(superuser: User) -> str:
    """
    Generate valid JWT token for SUPERUSER

    Expires in 24 hours (default)
    """
    token_data = {
        "sub": superuser.email,
        "user_id": superuser.id,
        "role": superuser.role.value
    }
    return create_access_token(token_data)


@pytest.fixture
def valid_admin_token(admin_user: User) -> str:
    """Generate valid JWT token for ADMIN"""
    token_data = {
        "sub": admin_user.email,
        "user_id": admin_user.id,
        "role": admin_user.role.value
    }
    return create_access_token(token_data)


@pytest.fixture
def valid_user_token(regular_user: User) -> str:
    """Generate valid JWT token for regular USER"""
    token_data = {
        "sub": regular_user.email,
        "user_id": regular_user.id,
        "role": regular_user.role.value
    }
    return create_access_token(token_data)


@pytest.fixture
def expired_token(superuser: User) -> str:
    """
    Generate expired JWT token

    Expired 1 hour ago
    """
    token_data = {
        "sub": superuser.email,
        "user_id": superuser.id,
        "role": superuser.role.value
    }
    expires_delta = timedelta(hours=-1)  # Already expired
    return create_access_token(token_data, expires_delta=expires_delta)


@pytest.fixture
def invalid_token() -> str:
    """
    Generate malformed JWT token

    Invalid signature
    """
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.INVALID.SIGNATURE"


@pytest.fixture
def token_with_invalid_user() -> str:
    """Generate token for non-existent user"""
    token_data = {
        "sub": "nonexistent@orizon.test",
        "user_id": "00000000-0000-0000-0000-000000000000",
        "role": "user"
    }
    return create_access_token(token_data)


# ============================================================================
# LEGACY FIXTURES (kept for backward compatibility)
# ============================================================================

@pytest.fixture
def test_user_data():
    """Sample user data for tests"""
    return {
        "email": "test@orizon.com",
        "password": TEST_PASSWORD,
        "full_name": "Test User",
        "role": "user"
    }


@pytest.fixture
def test_admin_data():
    """Sample admin data for tests"""
    return {
        "email": "admin@orizon.com",
        "password": TEST_PASSWORD,
        "full_name": "Admin User",
        "role": "admin"
    }


@pytest.fixture
def test_node_data():
    """Sample node data for tests"""
    return {
        "name": "test-node-001",
        "description": "Test node for unit tests",
        "node_type": "edge",
        "ip_address": "192.168.1.100"
    }


@pytest.fixture
def test_tunnel_data():
    """Sample tunnel data for tests"""
    return {
        "node_id": "test-node-001",
        "tunnel_type": "ssh",
        "agent_public_key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC...",
        "agent_ip": "192.168.1.100"
    }


@pytest.fixture
def test_acl_rule_data():
    """Sample ACL rule data for tests"""
    return {
        "source_node_id": "node-001",
        "dest_node_id": "node-002",
        "protocol": "tcp",
        "port": 22,
        "action": "allow",
        "priority": 50,
        "description": "Allow SSH from node-001 to node-002"
    }
