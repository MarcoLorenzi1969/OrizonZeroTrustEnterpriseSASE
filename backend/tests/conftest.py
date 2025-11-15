"""
Orizon Zero Trust Connect - PyTest Configuration
For: Marco @ Syneto/Orizon

Shared fixtures for all tests
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.config import settings
from app.main import app


# Test database URL (in-memory SQLite for speed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


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


@pytest.fixture
def test_user_data():
    """Sample user data for tests"""
    return {
        "email": "test@orizon.com",
        "password": "TestPassword123!",
        "full_name": "Test User",
        "role": "user"
    }


@pytest.fixture
def test_admin_data():
    """Sample admin data for tests"""
    return {
        "email": "admin@orizon.com",
        "password": "AdminPassword123!",
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
