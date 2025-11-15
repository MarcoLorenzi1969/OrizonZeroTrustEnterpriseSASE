#!/usr/bin/env python3
"""
Orizon Zero Trust Connect - Enhanced Agent with VNC Support
For: Marco @ Syneto/Orizon

WebSocket-based agent with VNC tunnel capabilities
"""

import asyncio
import websockets
import json
import socket
import platform
import psutil
import logging
import sys
import signal
from datetime import datetime
from pathlib import Path
from vnc_tunnel_handler import VNCTunnelHandler

__version__ = "1.1.0-vnc"


class OrizonAgentVNC:
    """
    Enhanced Orizon Agent with VNC Remote Desktop support

    Features:
    - WebSocket connection to hub
    - VNC tunnel management
    - System metrics collection
    - Heartbeat / keep-alive
    - Command handler (create_vnc_tunnel, close_vnc_tunnel, etc.)
    """

    def __init__(
        self,
        hub_host: str = "46.101.189.126",
        hub_ws_port: int = 8000,
        node_id: str = None,
        node_token: str = None,
    ):
        """
        Initialize agent

        Args:
            hub_host: Hub server hostname/IP
            hub_ws_port: Hub WebSocket port (FastAPI backend)
            node_id: Node identifier (auto-generated if None)
            node_token: Authentication token
        """
        self.hub_host = hub_host
        self.hub_ws_port = hub_ws_port
        self.node_id = node_id or self._generate_node_id()
        self.node_token = node_token
        self.running = True
        self.websocket = None

        # Setup logging
        self.setup_logging()

        # Initialize VNC tunnel handler
        self.vnc_handler = VNCTunnelHandler(hub_host=hub_host, logger=self.logger)

        # Heartbeat settings
        self.heartbeat_interval = 30  # seconds
        self.heartbeat_task = None

        self.logger.info(f"🚀 Orizon Agent VNC v{__version__} initialized")
        self.logger.info(f"📝 Node ID: {self.node_id}")
        self.logger.info(f"🌐 Hub: {self.hub_host}:{self.hub_ws_port}")

    def setup_logging(self):
        """Configure logging"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler("/var/log/orizon_agent_vnc.log"),
            ],
        )
        self.logger = logging.getLogger(__name__)

    def _generate_node_id(self) -> str:
        """Generate unique node ID"""
        import hashlib

        unique_string = f"{platform.node()}-{socket.gethostname()}"
        return hashlib.sha256(unique_string.encode()).hexdigest()[:16]

    async def connect(self):
        """Connect to hub via WebSocket"""
        ws_url = f"ws://{self.hub_host}:{self.hub_ws_port}/api/v1/nodes/ws/{self.node_id}"

        if self.node_token:
            ws_url += f"?token={self.node_token}"

        self.logger.info(f"🔗 Connecting to hub: {ws_url}")

        try:
            async with websockets.connect(
                ws_url,
                ping_interval=30,
                ping_timeout=10,
            ) as websocket:
                self.websocket = websocket
                self.logger.info("✅ Connected to hub")

                # Start heartbeat task
                self.heartbeat_task = asyncio.create_task(self.send_heartbeat())

                # Listen for messages
                await self.message_loop()

        except websockets.exceptions.ConnectionClosed:
            self.logger.warning("🔌 WebSocket connection closed")
        except Exception as e:
            self.logger.error(f"❌ WebSocket error: {e}")
        finally:
            # Cleanup
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
                try:
                    await self.heartbeat_task
                except asyncio.CancelledError:
                    pass

    async def message_loop(self):
        """Main message processing loop"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self.handle_message(data)
                except json.JSONDecodeError:
                    self.logger.error(f"❌ Invalid JSON: {message}")
                except Exception as e:
                    self.logger.error(f"❌ Error handling message: {e}")
        except Exception as e:
            self.logger.error(f"❌ Message loop error: {e}")

    async def handle_message(self, data: dict):
        """
        Handle incoming message from hub

        Supported actions:
        - create_vnc_tunnel: Create new VNC tunnel
        - close_vnc_tunnel: Close existing VNC tunnel
        - get_vnc_status: Get VNC tunnel status
        - get_metrics: Get system metrics
        """
        action = data.get("action")
        self.logger.info(f"📨 Received action: {action}")

        if action == "create_vnc_tunnel":
            await self.handle_create_vnc_tunnel(data)

        elif action == "close_vnc_tunnel":
            await self.handle_close_vnc_tunnel(data)

        elif action == "get_vnc_status":
            await self.handle_get_vnc_status(data)

        elif action == "get_metrics":
            await self.handle_get_metrics()

        elif action == "ping":
            await self.send_response({"type": "pong"})

        else:
            self.logger.warning(f"⚠️ Unknown action: {action}")
            await self.send_response({
                "type": "error",
                "error": "UNKNOWN_ACTION",
                "message": f"Unknown action: {action}",
            })

    async def handle_create_vnc_tunnel(self, data: dict):
        """Handle VNC tunnel creation request"""
        session_id = data.get("session_id")
        tunnel_port = data.get("tunnel_port")
        vnc_host = data.get("vnc_host", "localhost")
        vnc_port = data.get("vnc_port", 5900)

        self.logger.info(
            f"🔗 Creating VNC tunnel {session_id} to {self.hub_host}:{tunnel_port}"
        )

        success = await self.vnc_handler.create_tunnel(
            session_id=session_id,
            tunnel_port=tunnel_port,
            vnc_host=vnc_host,
            vnc_port=vnc_port,
        )

        if success:
            await self.send_response({
                "type": "vnc_tunnel_created",
                "session_id": session_id,
                "status": "success",
                "tunnel_port": tunnel_port,
            })
        else:
            await self.send_response({
                "type": "vnc_tunnel_error",
                "session_id": session_id,
                "status": "error",
                "error": "Failed to create VNC tunnel",
            })

    async def handle_close_vnc_tunnel(self, data: dict):
        """Handle VNC tunnel close request"""
        session_id = data.get("session_id")

        self.logger.info(f"🛑 Closing VNC tunnel {session_id}")

        success = await self.vnc_handler.close_tunnel(session_id)

        await self.send_response({
            "type": "vnc_tunnel_closed",
            "session_id": session_id,
            "status": "success" if success else "error",
        })

    async def handle_get_vnc_status(self, data: dict):
        """Get VNC tunnel status"""
        session_id = data.get("session_id")
        status = self.vnc_handler.get_tunnel_status(session_id)

        await self.send_response({
            "type": "vnc_status",
            "session_id": session_id,
            "status": status,
        })

    async def handle_get_metrics(self):
        """Send system metrics to hub"""
        metrics = self.collect_metrics()
        await self.send_response({
            "type": "metrics",
            "metrics": metrics,
        })

    def collect_metrics(self) -> dict:
        """Collect system metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            network = psutil.net_io_counters()

            return {
                "timestamp": datetime.utcnow().isoformat(),
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_mb": memory.used // 1024 // 1024,
                "memory_total_mb": memory.total // 1024 // 1024,
                "disk_percent": disk.percent,
                "disk_used_gb": disk.used // 1024 // 1024 // 1024,
                "disk_total_gb": disk.total // 1024 // 1024 // 1024,
                "network_bytes_sent": network.bytes_sent,
                "network_bytes_recv": network.bytes_recv,
                "vnc_tunnels_active": len(self.vnc_handler.get_active_tunnels()),
            }
        except Exception as e:
            self.logger.error(f"❌ Error collecting metrics: {e}")
            return {}

    async def send_heartbeat(self):
        """Send periodic heartbeat to hub"""
        while self.running:
            try:
                await asyncio.sleep(self.heartbeat_interval)

                # Collect and send metrics
                metrics = self.collect_metrics()

                await self.send_response({
                    "type": "heartbeat",
                    "node_id": self.node_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "metrics": metrics,
                    "active_vnc_tunnels": self.vnc_handler.get_active_tunnels(),
                })

                self.logger.debug(f"💓 Heartbeat sent")

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"❌ Heartbeat error: {e}")

    async def send_response(self, data: dict):
        """Send response to hub"""
        try:
            message = json.dumps(data)
            await self.websocket.send(message)
            self.logger.debug(f"📤 Sent: {data.get('type', 'unknown')}")
        except Exception as e:
            self.logger.error(f"❌ Error sending response: {e}")

    async def run(self):
        """Main run loop with reconnection"""
        retry_delay = 5

        while self.running:
            try:
                await self.connect()
            except KeyboardInterrupt:
                self.logger.info("🛑 Shutting down...")
                self.running = False
                break
            except Exception as e:
                self.logger.error(f"❌ Connection error: {e}")

            if self.running:
                self.logger.info(f"🔄 Reconnecting in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 300)  # Exponential backoff, max 5 min

    def stop(self):
        """Stop agent gracefully"""
        self.logger.info("🛑 Stopping agent...")
        self.running = False

        # Close all VNC tunnels
        for session_id in self.vnc_handler.get_active_tunnels():
            asyncio.create_task(self.vnc_handler.close_tunnel(session_id))


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Orizon Agent with VNC support")
    parser.add_argument("--hub-host", default="46.101.189.126", help="Hub hostname/IP")
    parser.add_argument("--hub-port", type=int, default=8000, help="Hub WebSocket port")
    parser.add_argument("--node-id", help="Node ID (auto-generated if not provided)")
    parser.add_argument("--token", help="Authentication token")

    args = parser.parse_args()

    # Create agent
    agent = OrizonAgentVNC(
        hub_host=args.hub_host,
        hub_ws_port=args.hub_port,
        node_id=args.node_id,
        node_token=args.token,
    )

    # Setup signal handlers
    def signal_handler(sig, frame):
        agent.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run agent
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
