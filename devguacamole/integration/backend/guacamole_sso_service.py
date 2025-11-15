"""
Orizon Guacamole SSO Service
Handles Single Sign-On integration between Orizon and Guacamole
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class GuacamoleSSO:
    """Guacamole SSO Service"""

    def __init__(
        self,
        guac_url: str,
        guac_datasource: str,
        guac_admin_user: str,
        guac_admin_pass: str,
        verify_ssl: bool = False
    ):
        self.guac_url = guac_url.rstrip('/')
        self.guac_datasource = guac_datasource
        self.guac_admin_user = guac_admin_user
        self.guac_admin_pass = guac_admin_pass
        self.verify_ssl = verify_ssl
        self._admin_token: Optional[str] = None
        self._token_expires: Optional[datetime] = None

    async def get_admin_token(self) -> str:
        """Get or refresh admin token for Guacamole API"""
        # Check if we have a valid token
        if self._admin_token and self._token_expires and datetime.utcnow() < self._token_expires:
            return self._admin_token

        # Request new token
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=self.verify_ssl)
        ) as session:
            url = f"{self.guac_url}/api/tokens"
            data = {
                'username': self.guac_admin_user,
                'password': self.guac_admin_pass
            }

            async with session.post(
                url,
                data=urlencode(data),
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Guacamole auth failed: {response.status} - {error_text}")

                result = await response.json()
                self._admin_token = result['authToken']
                # Tokens typically expire after 60 minutes, we'll refresh after 55
                self._token_expires = datetime.utcnow() + timedelta(minutes=55)

                logger.info("Guacamole admin token obtained")
                return self._admin_token

    async def authenticate_user(
        self,
        orizon_user_email: str,
        orizon_user_role: str
    ) -> Dict[str, str]:
        """
        Authenticate Orizon user with Guacamole via SSO
        Returns Guacamole credentials
        """
        # For admin/superuser, use admin credentials
        if orizon_user_role in ['superuser', 'admin']:
            return {
                'username': self.guac_admin_user,
                'password': self.guac_admin_pass
            }

        # For regular users, we would create/map Guacamole users
        # For now, return read-only credentials or provision user
        raise Exception("Non-admin SSO not yet implemented")

    async def get_user_token(
        self,
        guac_username: str,
        guac_password: str
    ) -> Dict:
        """Get Guacamole token for specific user"""
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=self.verify_ssl)
        ) as session:
            url = f"{self.guac_url}/api/tokens"
            data = {
                'username': guac_username,
                'password': guac_password
            }

            async with session.post(
                url,
                data=urlencode(data),
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Guacamole user auth failed: {response.status} - {error_text}")

                return await response.json()

    async def create_connection(
        self,
        name: str,
        protocol: str,
        hostname: str,
        port: int,
        username: str,
        password: str,
        **extra_params
    ) -> Dict:
        """Create a new Guacamole connection"""
        token = await self.get_admin_token()

        payload = {
            'name': name,
            'protocol': protocol,
            'parameters': {
                'hostname': hostname,
                'port': str(port),
                'username': username,
                'password': password,
                **extra_params
            },
            'attributes': {
                'max-connections': '2',
                'max-connections-per-user': '1'
            }
        }

        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=self.verify_ssl)
        ) as session:
            url = f"{self.guac_url}/api/session/data/{self.guac_datasource}/connections"
            headers = {
                'Content-Type': 'application/json',
                'Guacamole-Token': token
            }

            async with session.post(url, json=payload, headers=headers) as response:
                if response.status not in [200, 201]:
                    error_text = await response.text()
                    raise Exception(f"Failed to create connection: {response.status} - {error_text}")

                return await response.json()

    async def get_connections(self) -> Dict:
        """Get all Guacamole connections"""
        token = await self.get_admin_token()

        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=self.verify_ssl)
        ) as session:
            url = f"{self.guac_url}/api/session/data/{self.guac_datasource}/connections"
            headers = {'Guacamole-Token': token}

            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Failed to get connections: {response.status} - {error_text}")

                return await response.json()

    async def delete_connection(self, connection_id: str) -> None:
        """Delete a Guacamole connection"""
        token = await self.get_admin_token()

        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=self.verify_ssl)
        ) as session:
            url = f"{self.guac_url}/api/session/data/{self.guac_datasource}/connections/{connection_id}"
            headers = {'Guacamole-Token': token}

            async with session.delete(url, headers=headers) as response:
                if response.status not in [200, 204]:
                    error_text = await response.text()
                    raise Exception(f"Failed to delete connection: {response.status} - {error_text}")

    async def grant_connection_access(
        self,
        guac_username: str,
        connection_id: str,
        permissions: List[str] = None
    ) -> None:
        """Grant user access to a connection"""
        if permissions is None:
            permissions = ['READ']

        token = await self.get_admin_token()

        ops = [
            {
                'op': 'add',
                'path': f'/connectionPermissions/{connection_id}',
                'value': perm
            }
            for perm in permissions
        ]

        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=self.verify_ssl)
        ) as session:
            url = f"{self.guac_url}/api/session/data/{self.guac_datasource}/users/{guac_username}/permissions"
            headers = {
                'Content-Type': 'application/json',
                'Guacamole-Token': token
            }

            async with session.patch(url, json=ops, headers=headers) as response:
                if response.status != 204:
                    error_text = await response.text()
                    raise Exception(f"Failed to grant permissions: {response.status} - {error_text}")

    def get_connection_url(self, connection_id: str, token: str = None) -> str:
        """Get the URL to access a connection"""
        if token:
            return f"{self.guac_url}/#/client/{connection_id}?token={token}"
        return f"{self.guac_url}/#/client/{connection_id}"

    async def health_check(self) -> bool:
        """Check if Guacamole server is healthy"""
        try:
            token = await self.get_admin_token()
            return bool(token)
        except Exception as e:
            logger.error(f"Guacamole health check failed: {e}")
            return False
