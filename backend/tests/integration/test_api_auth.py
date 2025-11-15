"""
Integration tests for Authentication API
"""

import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
class TestAuthAPI:
    """Test authentication API endpoints"""

    async def test_health_endpoint(self):
        """Test health check endpoint"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    async def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": "nonexistent@orizon.com",
                    "password": "WrongPassword123!"
                }
            )

        assert response.status_code in [401, 404]

    async def test_metrics_endpoint(self):
        """Test Prometheus metrics endpoint"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/metrics")

        assert response.status_code == 200
        assert "orizon_" in response.text
