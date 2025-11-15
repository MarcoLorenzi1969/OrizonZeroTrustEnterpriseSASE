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
    
    async def public_key_auth_supported(self) -> bool:
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
            
            # Read authorized keys
            authorized_keys = asyncssh.read_authorized_keys(
                str(authorized_keys_path)
            )
            
            # Check if provided key is authorized
            key_data = key.export_public_key().decode()
            
            for auth_key in authorized_keys:
                if auth_key.export_public_key().decode() == key_data:
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
    
    async def server_requested(
        self,
        listen_host: str,
        listen_port: int,
        orig_host: str,
        orig_port: int
    ) -> bool:
        """
        Handle reverse port forwarding request
        
        This is called when an agent wants to create a reverse tunnel
        """
        conn = asyncssh.get_server_connection()
        username = conn.get_extra_info('username')
        
        logger.info(
            f"🔄 Reverse tunnel request from {username}: "
            f"{listen_host}:{listen_port} -> {orig_host}:{orig_port}"
        )
        
        try:
            # Generate tunnel ID
            tunnel_id = f"ssh_{username}_{listen_port}"
            node_id = username  # Assuming username == node_id
            
            # Register tunnel with manager
            async with self.db_session_factory() as db:
                tunnel = await tunnel_manager.register_tunnel(
                    db=db,
                    tunnel_id=tunnel_id,
                    node_id=node_id,
                    tunnel_type=TunnelType.SSH,
                    local_port=listen_port,
                    remote_port=orig_port,
                    connection_info={
                        "listen_host": listen_host,
                        "listen_port": listen_port,
                        "orig_host": orig_host,
                        "orig_port": orig_port,
                        "username": username
                    }
                )
                
                if tunnel:
                    # Track connection
                    ssh_conn = SSHTunnelConnection(
                        conn=conn,
                        username=username,
                        node_id=node_id,
                        tunnel_id=tunnel_id
                    )
                    ssh_conn.forwarded_ports.add(listen_port)
                    self.active_connections[tunnel_id] = ssh_conn
                    
                    logger.info(f"✅ Reverse tunnel established: {tunnel_id}")
                    return True
                else:
                    logger.error(f"❌ Failed to register tunnel: {tunnel_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error handling reverse tunnel request: {e}")
            return False
    
    def session_requested(self) -> asyncssh.SSHServerSession:
        """
        Handle session requests
        
        We don't allow interactive sessions, only port forwarding
        """
        logger.warning("⚠️ Interactive session requested (not allowed)")
        return asyncssh.EXTENDED_DATA_STDERR


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
