#!/usr/bin/env python3
"""
Orizon Zero Trust Connect - VNC Tunnel Handler
For: Marco @ Syneto/Orizon

Handles VNC tunnel creation on edge nodes for remote desktop access

Architecture:
    Hub FastAPI → WebSocket Command → Edge Agent → VNC Tunnel Handler
    VNC Tunnel: Hub:tunnel_port ←→ Edge:localhost:5900 (VNC server)
"""

import asyncio
import socket
import logging
from typing import Optional, Dict
from datetime import datetime


class VNCTunnelHandler:
    """
    VNC Tunnel Manager for Edge Agent

    Responsibilities:
    1. Receive tunnel creation commands from hub via WebSocket
    2. Create reverse TCP tunnel to hub:tunnel_port
    3. Forward traffic to local VNC server (localhost:5900)
    4. Monitor tunnel health and metrics
    5. Report status back to hub
    """

    def __init__(self, hub_host: str, logger: logging.Logger):
        """
        Initialize VNC Tunnel Handler

        Args:
            hub_host: Hub server hostname/IP
            logger: Logger instance
        """
        self.hub_host = hub_host
        self.logger = logger
        self.active_tunnels: Dict[str, asyncio.Task] = {}  # session_id → tunnel task
        self.tunnel_metrics: Dict[str, dict] = {}  # session_id → metrics

    async def create_tunnel(
        self,
        session_id: str,
        tunnel_port: int,
        vnc_host: str = "localhost",
        vnc_port: int = 5900,
    ) -> bool:
        """
        Create VNC reverse tunnel

        Args:
            session_id: Unique session identifier
            tunnel_port: Port on hub to connect to
            vnc_host: VNC server host on edge (usually localhost)
            vnc_port: VNC server port on edge (usually 5900)

        Returns:
            True if tunnel created successfully
        """
        if session_id in self.active_tunnels:
            self.logger.warning(f"⚠️ VNC tunnel {session_id} already exists")
            return False

        self.logger.info(
            f"🔗 Creating VNC tunnel {session_id}: {self.hub_host}:{tunnel_port} ← {vnc_host}:{vnc_port}"
        )

        try:
            # Check if VNC server is accessible
            if not self._check_vnc_server(vnc_host, vnc_port):
                self.logger.error(
                    f"❌ VNC server not accessible at {vnc_host}:{vnc_port}"
                )
                return False

            # Initialize metrics
            self.tunnel_metrics[session_id] = {
                "session_id": session_id,
                "tunnel_port": tunnel_port,
                "vnc_host": vnc_host,
                "vnc_port": vnc_port,
                "bytes_sent": 0,
                "bytes_received": 0,
                "started_at": datetime.utcnow().isoformat(),
                "status": "connecting",
            }

            # Create tunnel task
            tunnel_task = asyncio.create_task(
                self._run_tunnel(session_id, tunnel_port, vnc_host, vnc_port)
            )

            self.active_tunnels[session_id] = tunnel_task

            self.logger.info(f"✅ VNC tunnel {session_id} created")
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to create VNC tunnel {session_id}: {e}")
            return False

    async def close_tunnel(self, session_id: str) -> bool:
        """
        Close VNC tunnel

        Args:
            session_id: Session identifier

        Returns:
            True if tunnel closed successfully
        """
        if session_id not in self.active_tunnels:
            self.logger.warning(f"⚠️ VNC tunnel {session_id} not found")
            return False

        self.logger.info(f"🛑 Closing VNC tunnel {session_id}")

        try:
            # Cancel tunnel task
            task = self.active_tunnels[session_id]
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

            # Remove from active tunnels
            del self.active_tunnels[session_id]

            # Update metrics
            if session_id in self.tunnel_metrics:
                self.tunnel_metrics[session_id]["status"] = "closed"
                self.tunnel_metrics[session_id]["ended_at"] = datetime.utcnow().isoformat()

            self.logger.info(f"✅ VNC tunnel {session_id} closed")
            return True

        except Exception as e:
            self.logger.error(f"❌ Error closing VNC tunnel {session_id}: {e}")
            return False

    def get_tunnel_status(self, session_id: str) -> Optional[dict]:
        """Get tunnel status and metrics"""
        return self.tunnel_metrics.get(session_id)

    def get_active_tunnels(self) -> list:
        """Get list of active tunnel session IDs"""
        return list(self.active_tunnels.keys())

    async def _run_tunnel(
        self,
        session_id: str,
        tunnel_port: int,
        vnc_host: str,
        vnc_port: int,
    ):
        """
        Run reverse tunnel (main tunnel loop)

        This creates a persistent connection to hub:tunnel_port
        and forwards all traffic to vnc_host:vnc_port
        """
        retry_count = 0
        max_retries = 5
        retry_delay = 5

        while retry_count < max_retries:
            hub_socket = None
            vnc_socket = None

            try:
                # Connect to hub tunnel port
                self.logger.debug(
                    f"🔗 Connecting to hub tunnel {self.hub_host}:{tunnel_port}"
                )
                hub_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                hub_socket.settimeout(10)
                hub_socket.connect((self.hub_host, tunnel_port))
                hub_socket.setblocking(False)

                self.logger.info(
                    f"✅ Connected to hub tunnel {self.hub_host}:{tunnel_port}"
                )

                # Update metrics
                self.tunnel_metrics[session_id]["status"] = "active"

                # Accept incoming connection from VNC Gateway
                # Actually, this is a direct forward, so we connect to VNC immediately
                vnc_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                vnc_socket.settimeout(10)
                vnc_socket.connect((vnc_host, vnc_port))
                vnc_socket.setblocking(False)

                self.logger.info(f"✅ Connected to VNC server {vnc_host}:{vnc_port}")

                # Start bidirectional forwarding
                await self._forward_traffic(
                    session_id, hub_socket, vnc_socket
                )

                # If we get here, connection closed normally
                self.logger.info(f"🔌 VNC tunnel {session_id} closed normally")
                break

            except asyncio.CancelledError:
                self.logger.info(f"🛑 VNC tunnel {session_id} cancelled")
                break
            except Exception as e:
                retry_count += 1
                self.logger.error(
                    f"❌ VNC tunnel {session_id} error (attempt {retry_count}/{max_retries}): {e}"
                )

                if retry_count < max_retries:
                    self.logger.info(f"🔄 Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 60)  # Exponential backoff
            finally:
                # Cleanup sockets
                if hub_socket:
                    try:
                        hub_socket.close()
                    except:
                        pass
                if vnc_socket:
                    try:
                        vnc_socket.close()
                    except:
                        pass

        # Update metrics on exit
        if session_id in self.tunnel_metrics:
            self.tunnel_metrics[session_id]["status"] = "disconnected"

    async def _forward_traffic(
        self, session_id: str, hub_socket: socket.socket, vnc_socket: socket.socket
    ):
        """
        Forward traffic bidirectionally between hub and VNC server

        Hub ←→ VNC Server
        """
        loop = asyncio.get_event_loop()

        async def hub_to_vnc():
            """Forward data from hub to VNC server"""
            try:
                while True:
                    data = await loop.sock_recv(hub_socket, 8192)
                    if not data:
                        self.logger.debug(f"🔌 Hub socket closed for {session_id}")
                        break

                    await loop.sock_sendall(vnc_socket, data)
                    self.tunnel_metrics[session_id]["bytes_received"] += len(data)
                    self.logger.debug(
                        f"📥 Hub→VNC: {len(data)} bytes for {session_id}"
                    )
            except Exception as e:
                self.logger.error(f"❌ Error Hub→VNC for {session_id}: {e}")

        async def vnc_to_hub():
            """Forward data from VNC server to hub"""
            try:
                while True:
                    data = await loop.sock_recv(vnc_socket, 8192)
                    if not data:
                        self.logger.debug(f"🔌 VNC socket closed for {session_id}")
                        break

                    await loop.sock_sendall(hub_socket, data)
                    self.tunnel_metrics[session_id]["bytes_sent"] += len(data)
                    self.logger.debug(
                        f"📤 VNC→Hub: {len(data)} bytes for {session_id}"
                    )
            except Exception as e:
                self.logger.error(f"❌ Error VNC→Hub for {session_id}: {e}")

        # Run both directions concurrently
        try:
            await asyncio.gather(hub_to_vnc(), vnc_to_hub())
        except Exception as e:
            self.logger.error(f"❌ Error in bidirectional forwarding for {session_id}: {e}")

    def _check_vnc_server(self, host: str, port: int) -> bool:
        """
        Check if VNC server is accessible

        Args:
            host: VNC server host
            port: VNC server port

        Returns:
            True if VNC server is accessible
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception as e:
            self.logger.error(f"❌ Error checking VNC server: {e}")
            return False


# Standalone test function
async def test_vnc_tunnel():
    """Test VNC tunnel handler"""
    import sys

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("🧪 Testing VNC Tunnel Handler")
    logger.info("=" * 60)

    # Create handler
    handler = VNCTunnelHandler(hub_host="46.101.189.126", logger=logger)

    # Test tunnel creation
    success = await handler.create_tunnel(
        session_id="test-session-123",
        tunnel_port=50000,
        vnc_host="localhost",
        vnc_port=5900,
    )

    if success:
        logger.info("✅ Tunnel created successfully")

        # Wait 10 seconds
        await asyncio.sleep(10)

        # Get status
        status = handler.get_tunnel_status("test-session-123")
        logger.info(f"📊 Tunnel status: {status}")

        # Close tunnel
        await handler.close_tunnel("test-session-123")
        logger.info("✅ Tunnel closed")
    else:
        logger.error("❌ Failed to create tunnel")


if __name__ == "__main__":
    # Run test
    asyncio.run(test_vnc_tunnel())
