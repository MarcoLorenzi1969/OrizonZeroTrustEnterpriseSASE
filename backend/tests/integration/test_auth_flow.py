"""
Integration tests for Authentication Flow

Tests the complete authentication cycle:
- Login
- Token refresh
- Logout
- Protected endpoints access
"""

import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
class TestLoginLogout:
    """Test login and logout flow"""

    async def test_login_success(self, superuser):
        """
        Test successful login
        
        Given: Valid credentials
        When: POSTing to /api/v1/auth/login
        Then: Should return access and refresh tokens
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": superuser.email,
                    "password": "TestPassword123!"  # Assuming this is the test password
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        
    async def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": "wrong@example.com",
                    "password": "WrongPassword"
                }
            )
        
        assert response.status_code == 401
        
    async def test_logout(self, superuser):
        """Test logout endpoint"""
        # First login
        async with AsyncClient(app=app, base_url="http://test") as client:
            login_response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": superuser.email,
                    "password": "TestPassword123!"
                }
            )
            
            token = login_response.json()["access_token"]
            
            # Then logout
            logout_response = await client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert logout_response.status_code == 200
            data = logout_response.json()
            assert "message" in data


@pytest.mark.asyncio
class TestTokenRefresh:
    """Test token refresh functionality"""

    async def test_refresh_token(self, superuser):
        """Test refreshing access token"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Login
            login_response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": superuser.email,
                    "password": "TestPassword123!"
                }
            )
            
            refresh_token = login_response.json()["refresh_token"]
            
            # Refresh
            refresh_response = await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": refresh_token}
            )
            
            assert refresh_response.status_code == 200
            data = refresh_response.json()
            assert "access_token" in data
            assert "refresh_token" in data


@pytest.mark.asyncio
class TestProtectedEndpoints:
    """Test access to protected endpoints"""

    async def test_me_endpoint_authenticated(self, superuser):
        """Test /api/v1/auth/me with valid token"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Login
            login_response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": superuser.email,
                    "password": "TestPassword123!"
                }
            )
            
            token = login_response.json()["access_token"]
            
            # Get user info
            me_response = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert me_response.status_code == 200
            data = me_response.json()
            assert data["email"] == superuser.email
            assert data["id"] == superuser.id
            
    async def test_me_endpoint_unauthenticated(self):
        """Test /api/v1/auth/me without token"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/auth/me")
            
            assert response.status_code == 401
            
    async def test_groups_endpoint_requires_auth(self):
        """Test /api/v1/groups requires authentication"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/groups")
            
            assert response.status_code == 401


@pytest.mark.asyncio  
class TestRoleBasedAccess:
    """Test role-based access control"""

    async def test_admin_can_create_group(self, admin_user):
        """Test ADMIN role can create groups"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Login as admin
            login_response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": admin_user.email,
                    "password": "AdminPassword123!"
                }
            )
            
            token = login_response.json()["access_token"]
            
            # Create group
            create_response = await client.post(
                "/api/v1/groups",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "name": "Test Group",
                    "description": "Created by admin"
                }
            )
            
            # Admin should be able to create
            assert create_response.status_code in [200, 201]
            
    async def test_regular_user_cannot_create_group(self, regular_user):
        """Test regular USER cannot create groups"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Login as regular user
            login_response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": regular_user.email,
                    "password": "UserPassword123!"
                }
            )
            
            token = login_response.json()["access_token"]
            
            # Try to create group
            create_response = await client.post(
                "/api/v1/groups",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "name": "Test Group",
                    "description": "Attempt by regular user"
                }
            )
            
            # Should be forbidden
            assert create_response.status_code == 403
