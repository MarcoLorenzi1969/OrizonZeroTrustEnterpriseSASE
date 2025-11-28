"""
SSH Reverse Tunnel Server
For: Marco @ Syneto/Orizon

Handles SSH reverse tunnels from agents
"""

import asyncio
import asyncssh
from typing import Optional, Dict, Set
from datetime import datetime
from loguru import logger
from pathlib import Path

from app.core.config import settings
from app.tunnel.manager import tunnel_manager
from app.models.tunnel import TunnelType


class SSHTunnelConnection:
    """Represents a single SSH tunnel connection"""
    
    def __init__(
        self,
        conn: asyncssh.SSHServerConnection,
        username: str,
        node_id: str,
        tunnel_id: str
    ):
        self.conn = conn
        self.username = username
        self.node_id = node_id
        self.tunnel_id = tunnel_id
        self.connected_at = datetime.utcnow()
        self.forwarded_ports: Set[int] = set()
    
    async def close(self):
        """Close the SSH connection"""
        try:
            self.conn.close()
            await self.conn.wait_closed()
        except Exception as e:
            logger.error(f"Error closing SSH connection: {e}")


class SSHReverseServer(asyncssh.SSHServer):
    """
    SSH Server for handling reverse tunnel connections
    
    Security features:
    - Public key authentication only
    - Per-user authorized_keys
    - Connection logging and audit
    - Rate limiting (TODO)
    """
    
    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
        self.active_connections: Dict[str, SSHTunnelConnection] = {}
    
    def connection_made(self, conn: asyncssh.SSHServerConnection):
        """Called when SSH connection is established"""
        peer = conn.get_extra_info('peername')
        logger.info(f"🔌 SSH connection from {peer}")
    
    def connection_lost(self, exc: Optional[Exception]):
        """Called when SSH connection is lost"""
        if exc:
            logger.warning(f"SSH connection lost: {exc}")
        else:
            logger.info("SSH connection closed normally")
    
    def begin_auth(self, username: str) -> bool:
        """
        Begin authentication for a user
        
        Returns True to allow authentication attempts
        """
        logger.info(f"🔐 Authentication attempt for user: {username}")
        return True
    
    def public_key_auth_supported(self) -> bool:
        """Enable public key authentication"""
        return True
    
    async def validate_public_key(
        self,
        username: str,
        key: asyncssh.SSHKey
    ) -> bool:
        """
        Validate public key for authentication

        Checks against authorized_keys file
        """
        try:
            # Load authorized keys for this user
            authorized_keys_path = Path(settings.SSH_AUTHORIZED_KEYS_PATH) / username

            if not authorized_keys_path.exists():
                logger.warning(f"⚠️ No authorized_keys for user: {username}")
                return False

            # Read authorized keys file
            authorized_keys = asyncssh.read_authorized_keys(
                str(authorized_keys_path)
            )

            # Simple key comparison - check if the key data matches
            provided_key_data = key.export_public_key('openssh').decode().strip()

            with open(authorized_keys_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Extract key data (format: type key comment)
                        parts = line.split()
                        if len(parts) >= 2:
                            stored_key = f"{parts[0]} {parts[1]}"
                            # Extract just type and key from provided key
                            provided_parts = provided_key_data.split()
                            if len(provided_parts) >= 2:
                                provided_key = f"{provided_parts[0]} {provided_parts[1]}"
                                if stored_key == provided_key:
                                    logger.info(f"✅ Public key validated for user: {username}")
                                    return True

            logger.warning(f"❌ Invalid public key for user: {username}")
            return False

        except Exception as e:
            logger.error(f"Error validating public key: {e}")
            return False
    
    def password_auth_supported(self) -> bool:
        """Disable password authentication"""
        return False
    
    def server_requested(self, listen_host: str, listen_port: int) -> bool:
        """
        Handle reverse port forwarding request (TCP/IP forwarding)

        This is called when an agent wants to create a reverse tunnel.
        In asyncssh, this receives only listen_host and listen_port.
        """
        logger.info(f"🔄 Reverse tunnel request: {listen_host}:{listen_port}")

        # Allow all reverse port forwarding requests
        # The actual tunnel tracking is simplified since we're inside Docker
        return True
    
    def session_requested(self) -> bool:
        """
        Handle session requests

        Allow sessions for interactive terminal access via reverse tunnel.
        The actual session handling is done through port forwarding,
        where the backend connects to the forwarded SSH port.
        """
        logger.info("📟 Interactive session requested")
        return True

    def pty_requested(
        self,
        term_type: str,
        term_size: tuple,
        term_modes: dict
    ) -> bool:
        """
        Handle PTY (pseudo-terminal) requests

        Allow PTY allocation for terminal sessions.
        """
        logger.info(f"📺 PTY requested: term={term_type}, size={term_size}")
        return True

    def shell_requested(self) -> bool:
        """
        Handle shell requests

        We don't provide direct shell access on the hub.
        Interactive terminals are accessed through port forwarding.
        """
        logger.warning("⚠️ Shell requested on hub (redirecting to forwarded port)")
        return False


class SSHReverseServerManager:
    """Manager for SSH Reverse Server"""
    
    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
        self.server: Optional[asyncssh.SSHAcceptor] = None
        self.ssh_server_instance: Optional[SSHReverseServer] = None
    
    async def start(self):
        """Start SSH reverse tunnel server"""
        try:
            logger.info(f"🚀 Starting SSH Reverse Server on port {settings.TUNNEL_SSH_PORT}")
            
            # Load or generate host key
            host_key_path = Path(settings.SSH_HOST_KEY_PATH)
            if not host_key_path.exists():
                logger.info("📝 Generating new SSH host key...")
                host_key_path.parent.mkdir(parents=True, exist_ok=True)
                key = asyncssh.generate_private_key('ssh-rsa')
                host_key_path.write_bytes(key.export_private_key())
                logger.info("✅ SSH host key generated")
            
            # Create SSH server instance
            self.ssh_server_instance = SSHReverseServer(self.db_session_factory)
            
            # Start server
            self.server = await asyncssh.listen(
                host='0.0.0.0',
                port=settings.TUNNEL_SSH_PORT,
                server_host_keys=[str(host_key_path)],
                server_factory=lambda: self.ssh_server_instance,
                encoding=None,
                process_factory=None
            )
            
            logger.info(
                f"✅ SSH Reverse Server started on "
                f"0.0.0.0:{settings.TUNNEL_SSH_PORT}"
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to start SSH Reverse Server: {e}")
            raise
    
    async def stop(self):
        """Stop SSH reverse tunnel server"""
        if self.server:
            logger.info("⏹️ Stopping SSH Reverse Server...")
            self.server.close()
            await self.server.wait_closed()
            logger.info("✅ SSH Reverse Server stopped")
    
    async def get_active_connections(self) -> Dict[str, SSHTunnelConnection]:
        """Get all active SSH tunnel connections"""
        if self.ssh_server_instance:
            return self.ssh_server_instance.active_connections
        return {}


# Global SSH server manager instance
ssh_server_manager: Optional[SSHReverseServerManager] = None


def init_ssh_server(db_session_factory):
    """Initialize SSH server manager"""
    global ssh_server_manager
    ssh_server_manager = SSHReverseServerManager(db_session_factory)
    return ssh_server_manager
