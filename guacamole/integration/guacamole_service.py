"""
Orizon Zero Trust Connect - Guacamole Integration Service

This service provides integration between Orizon ZTC and Apache Guacamole,
enabling web-based SSH/RDP/VNC access to edge nodes through Guacamole gateway.
"""

import aiohttp
import asyncio
import hashlib
import base64
import json
from typing import Optional, Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class GuacamoleAPIClient:
    """Apache Guacamole REST API Client"""

    def __init__(self, base_url: str, username: str, password: str):
        """
        Initialize Guacamole API client

        Args:
            base_url: Guacamole server URL (e.g., https://167.71.33.70)
            username: Guacamole admin username
            password: Guacamole admin password
        """
        self.base_url = base_url.rstrip('/')
        self.api_base = f"{self.base_url}/guacamole/api"
        self.username = username
        self.password = password
        self.token: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        await self.authenticate()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def authenticate(self) -> str:
        """
        Authenticate with Guacamole and get auth token

        Returns:
            Authentication token
        """
        url = f"{self.api_base}/tokens"
        data = {
            'username': self.username,
            'password': self.password
        }

        async with self.session.post(url, data=data, ssl=False) as response:
            if response.status != 200:
                raise Exception(f"Authentication failed: {response.status}")

            result = await response.json()
            self.token = result['authToken']
            logger.info(f"Authenticated with Guacamole as {self.username}")
            return self.token

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """
        Make authenticated request to Guacamole API

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (without /api prefix)
            **kwargs: Additional request parameters

        Returns:
            Response JSON
        """
        if not self.token:
            await self.authenticate()

        url = f"{self.api_base}/{endpoint}"
        params = kwargs.get('params', {})
        params['token'] = self.token
        kwargs['params'] = params
        kwargs['ssl'] = False

        async with self.session.request(method, url, **kwargs) as response:
            if response.status == 401:
                # Token expired, re-authenticate
                await self.authenticate()
                params['token'] = self.token
                async with self.session.request(method, url, **kwargs) as retry:
                    return await retry.json()

            if response.status >= 400:
                text = await response.text()
                raise Exception(f"API request failed: {response.status} - {text}")

            return await response.json()

    async def create_ssh_connection(
        self,
        name: str,
        hostname: str,
        port: int = 22,
        username: str = None,
        password: str = None,
        private_key: str = None,
        parent_id: str = "ROOT"
    ) -> Dict:
        """
        Create SSH connection in Guacamole

        Args:
            name: Connection display name
            hostname: SSH server hostname/IP
            port: SSH port (default 22)
            username: SSH username (optional if using key)
            password: SSH password (optional)
            private_key: SSH private key (optional)
            parent_id: Parent connection group ID

        Returns:
            Created connection object
        """
        connection = {
            "parentIdentifier": parent_id,
            "name": name,
            "protocol": "ssh",
            "parameters": {
                "hostname": hostname,
                "port": str(port),
                "enable-sftp": "true",
                "sftp-root-directory": "/",
                "color-scheme": "gray-black",
                "font-name": "monospace",
                "font-size": "12",
                "scrollback": "10000",
                "timezone": "Europe/Rome"
            },
            "attributes": {
                "max-connections": "5",
                "max-connections-per-user": "2"
            }
        }

        # Add credentials
        if username:
            connection["parameters"]["username"] = username
        if password:
            connection["parameters"]["password"] = password
        if private_key:
            connection["parameters"]["private-key"] = private_key

        result = await self._request(
            'POST',
            'session/data/mysql/connections',
            json=connection
        )

        logger.info(f"Created SSH connection: {name} -> {hostname}:{port}")
        return result

    async def create_rdp_connection(
        self,
        name: str,
        hostname: str,
        port: int = 3389,
        username: str = None,
        password: str = None,
        domain: str = None,
        parent_id: str = "ROOT"
    ) -> Dict:
        """
        Create RDP connection in Guacamole

        Args:
            name: Connection display name
            hostname: RDP server hostname/IP
            port: RDP port (default 3389)
            username: Windows username
            password: Windows password
            domain: Windows domain (optional)
            parent_id: Parent connection group ID

        Returns:
            Created connection object
        """
        connection = {
            "parentIdentifier": parent_id,
            "name": name,
            "protocol": "rdp",
            "parameters": {
                "hostname": hostname,
                "port": str(port),
                "security": "any",
                "ignore-cert": "true",
                "enable-drive": "true",
                "drive-path": "/tmp",
                "create-drive-path": "true",
                "console-audio": "true",
                "disable-audio": "false",
                "enable-printing": "true",
                "enable-wallpaper": "false",
                "color-depth": "16"
            },
            "attributes": {
                "max-connections": "3",
                "max-connections-per-user": "1"
            }
        }

        if username:
            connection["parameters"]["username"] = username
        if password:
            connection["parameters"]["password"] = password
        if domain:
            connection["parameters"]["domain"] = domain

        result = await self._request(
            'POST',
            'session/data/mysql/connections',
            json=connection
        )

        logger.info(f"Created RDP connection: {name} -> {hostname}:{port}")
        return result

    async def list_connections(self) -> List[Dict]:
        """
        List all connections in Guacamole

        Returns:
            List of connection objects
        """
        result = await self._request('GET', 'session/data/mysql/connections')
        return list(result.values())

    async def get_connection(self, connection_id: str) -> Dict:
        """
        Get connection details

        Args:
            connection_id: Connection ID

        Returns:
            Connection object
        """
        return await self._request(
            'GET',
            f'session/data/mysql/connections/{connection_id}'
        )

    async def delete_connection(self, connection_id: str) -> None:
        """
        Delete connection

        Args:
            connection_id: Connection ID
        """
        await self._request(
            'DELETE',
            f'session/data/mysql/connections/{connection_id}'
        )
        logger.info(f"Deleted connection: {connection_id}")

    async def get_active_sessions(self) -> List[Dict]:
        """
        Get list of active sessions

        Returns:
            List of active session objects
        """
        result = await self._request('GET', 'session/data/mysql/activeConnections')
        return list(result.values())

    async def create_user(
        self,
        username: str,
        password: str,
        attributes: Dict = None
    ) -> Dict:
        """
        Create Guacamole user

        Args:
            username: Username
            password: Password
            attributes: Additional user attributes

        Returns:
            Created user object
        """
        user = {
            "username": username,
            "password": password,
            "attributes": attributes or {
                "disabled": "",
                "expired": "",
                "access-window-start": "",
                "access-window-end": "",
                "valid-from": "",
                "valid-until": "",
                "timezone": "Europe/Rome"
            }
        }

        result = await self._request(
            'POST',
            'session/data/mysql/users',
            json=user
        )

        logger.info(f"Created user: {username}")
        return result

    async def grant_connection_permission(
        self,
        username: str,
        connection_id: str
    ) -> None:
        """
        Grant user permission to access connection

        Args:
            username: Username
            connection_id: Connection ID
        """
        permissions = [{
            "op": "add",
            "path": f"/connectionPermissions/{connection_id}",
            "value": "READ"
        }]

        await self._request(
            'PATCH',
            f'session/data/mysql/users/{username}/permissions',
            json=permissions
        )

        logger.info(f"Granted {username} access to connection {connection_id}")


class GuacamoleIntegrationService:
    """Service to integrate Guacamole with Orizon ZTC"""

    def __init__(
        self,
        guac_url: str,
        guac_username: str,
        guac_password: str,
        orizon_db
    ):
        """
        Initialize Guacamole integration service

        Args:
            guac_url: Guacamole server URL
            guac_username: Guacamole admin username
            guac_password: Guacamole admin password
            orizon_db: Orizon database session
        """
        self.guac_url = guac_url
        self.guac_username = guac_username
        self.guac_password = guac_password
        self.db = orizon_db
        self.client: Optional[GuacamoleAPIClient] = None

    async def sync_node_to_guacamole(self, node_id: str) -> Optional[str]:
        """
        Sync Orizon node to Guacamole as SSH connection

        Args:
            node_id: Orizon node ID

        Returns:
            Guacamole connection ID if successful
        """
        # Get node from database
        from sqlalchemy import text
        result = await self.db.execute(
            text("SELECT id, name, ip_address FROM nodes WHERE id = :id"),
            {"id": node_id}
        )
        node = result.fetchone()

        if not node:
            logger.warning(f"Node {node_id} not found in database")
            return None

        # Get SSH credentials for node (TODO: implement secure credential storage)
        ssh_username = "parallels"  # Default for now
        ssh_password = "profano.69"  # Should be encrypted in DB

        # Create connection in Guacamole
        async with GuacamoleAPIClient(
            self.guac_url,
            self.guac_username,
            self.guac_password
        ) as client:
            connection = await client.create_ssh_connection(
                name=f"Orizon - {node.name}",
                hostname=node.ip_address or "10.211.55.19",  # Fallback IP
                port=22,
                username=ssh_username,
                password=ssh_password
            )

            # Save connection ID in Orizon database
            await self.db.execute(
                text("""
                    UPDATE nodes
                    SET guacamole_connection_id = :conn_id
                    WHERE id = :node_id
                """),
                {
                    "conn_id": connection["identifier"],
                    "node_id": node_id
                }
            )
            await self.db.commit()

            return connection["identifier"]

    async def get_guacamole_url_for_node(self, node_id: str) -> Optional[str]:
        """
        Get Guacamole web URL to access node via SSH

        Args:
            node_id: Orizon node ID

        Returns:
            Guacamole connection URL
        """
        result = await self.db.execute(
            text("SELECT guacamole_connection_id FROM nodes WHERE id = :id"),
            {"id": node_id}
        )
        row = result.fetchone()

        if not row or not row.guacamole_connection_id:
            # Try to sync node
            conn_id = await self.sync_node_to_guacamole(node_id)
            if not conn_id:
                return None
        else:
            conn_id = row.guacamole_connection_id

        # Generate Guacamole client URL
        # Format: https://GUAC_SERVER/guacamole/#/client/CONNECTION_ID
        return f"{self.guac_url}/guacamole/#/client/{conn_id}"

    async def sync_all_nodes(self) -> int:
        """
        Sync all Orizon nodes to Guacamole

        Returns:
            Number of nodes synced
        """
        result = await self.db.execute(
            text("SELECT id FROM nodes WHERE status = 'online'")
        )
        nodes = result.fetchall()

        synced = 0
        for node in nodes:
            try:
                conn_id = await self.sync_node_to_guacamole(node.id)
                if conn_id:
                    synced += 1
            except Exception as e:
                logger.error(f"Failed to sync node {node.id}: {e}")

        logger.info(f"Synced {synced}/{len(nodes)} nodes to Guacamole")
        return synced
