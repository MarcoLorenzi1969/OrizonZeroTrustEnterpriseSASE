#!/usr/bin/env python3
"""
Orizon Zero Trust Connect - VNC Gateway Service
For: Marco @ Syneto/Orizon

WebSocket ↔ TCP Proxy for VNC connections with JWT validation

Architecture:
    Browser (noVNC) → WebSocket → VNC Gateway → TCP Tunnel → Edge Agent → VNC Server

This service:
1. Accepts WebSocket connections from noVNC clients
2. Validates JWT session tokens
3. Proxies RFB (VNC protocol) traffic to tunnel port
4. Reports metrics back to FastAPI backend
"""

import asyncio
import websockets
import socket
import jwt
import json
import os
import sys
import struct
from typing import Optional, Dict
from datetime import datetime
from loguru import logger
from urllib.parse import parse_qs


# Configuration from environment variables
JWT_SECRET = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
GATEWAY_HOST = os.getenv("VNC_GATEWAY_HOST", "0.0.0.0")
GATEWAY_PORT = int(os.getenv("VNC_GATEWAY_PORT", "6080"))
TUNNEL_HOST = os.getenv("TUNNEL_HOST", "localhost")  # Where tunnels are exposed


# Metrics tracking
active_sessions: Dict[str, dict] = {}


class VNCGateway:
    """
    VNC WebSocket ↔ TCP Gateway

    Handles:
    - JWT token validation
    - WebSocket connection from browser
    - TCP connection to tunnel port
    - Bidirectional byte forwarding
    - Connection metrics and health monitoring
    """

    def __init__(self):
        self.active_connections = 0
        self.total_connections = 0

    async def handle_connection(self, websocket, path: str):
        """
        Handle incoming WebSocket connection from noVNC client

        URL format: ws://gateway:6080/vnc/{session_id}?token={jwt}
        """
        session_id = None
        tcp_socket = None
        client_ip = websocket.remote_address[0] if websocket.remote_address else "unknown"

        try:
            # Parse path to extract session_id
            # Path format: /vnc/{session_id}
            path_parts = path.strip("/").split("/")
            if len(path_parts) < 2 or path_parts[0] != "vnc":
                logger.warning(f"⚠️ Invalid path: {path}")
                await websocket.send(json.dumps({
                    "error": "INVALID_PATH",
                    "message": "Path must be /vnc/{session_id}"
                }))
                await websocket.close(code=1008)
                return

            session_id = path_parts[1]

            # Extract token from query parameters
            # websockets library doesn't parse query params, we need to do it manually
            # The 'path' variable contains the full path with query string
            if "?" in path:
                query_string = path.split("?", 1)[1]
                params = parse_qs(query_string)
                token = params.get("token", [None])[0]
            else:
                token = None

            if not token:
                logger.warning(f"⚠️ No token provided for session {session_id}")
                await websocket.send(json.dumps({
                    "error": "NO_TOKEN",
                    "message": "JWT token is required"
                }))
                await websocket.close(code=1008)
                return

            # Validate JWT token
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
                logger.debug(f"🔐 JWT payload: {payload}")
            except jwt.ExpiredSignatureError:
                logger.warning(f"⚠️ Expired token for session {session_id}")
                await websocket.send(json.dumps({
                    "error": "TOKEN_EXPIRED",
                    "message": "Session token has expired"
                }))
                await websocket.close(code=4001)
                return
            except jwt.InvalidTokenError as e:
                logger.warning(f"⚠️ Invalid token for session {session_id}: {e}")
                await websocket.send(json.dumps({
                    "error": "INVALID_TOKEN",
                    "message": f"Invalid token: {str(e)}"
                }))
                await websocket.close(code=4002)
                return

            # Verify session_id matches token
            if payload.get("session_id") != session_id:
                logger.warning(f"⚠️ Session ID mismatch for {session_id}")
                await websocket.send(json.dumps({
                    "error": "SESSION_MISMATCH",
                    "message": "Session ID does not match token"
                }))
                await websocket.close(code=4003)
                return

            # Get tunnel port from token
            tunnel_port = payload.get("tunnel_port")
            if not tunnel_port:
                logger.error(f"❌ No tunnel_port in token for session {session_id}")
                await websocket.send(json.dumps({
                    "error": "NO_TUNNEL_PORT",
                    "message": "Token does not contain tunnel port"
                }))
                await websocket.close(code=4004)
                return

            logger.info(f"✅ Session {session_id} validated - connecting to tunnel port {tunnel_port}")

            # Connect to tunnel port (TCP)
            try:
                tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                tcp_socket.settimeout(10)
                tcp_socket.connect((TUNNEL_HOST, tunnel_port))
                tcp_socket.setblocking(False)
                logger.info(f"✅ Connected to tunnel {TUNNEL_HOST}:{tunnel_port}")
            except Exception as e:
                logger.error(f"❌ Failed to connect to tunnel port {tunnel_port}: {e}")
                await websocket.send(json.dumps({
                    "error": "TUNNEL_CONNECTION_FAILED",
                    "message": f"Cannot connect to VNC tunnel: {str(e)}"
                }))
                await websocket.close(code=1011)
                return

            # Send success message
            await websocket.send(json.dumps({
                "status": "CONNECTED",
                "session_id": session_id,
                "message": "VNC Gateway connected to tunnel"
            }))

            # Track metrics
            self.active_connections += 1
            self.total_connections += 1

            metrics = {
                "session_id": session_id,
                "bytes_sent": 0,
                "bytes_received": 0,
                "frames_sent": 0,
                "started_at": datetime.utcnow().isoformat(),
                "client_ip": client_ip,
            }
            active_sessions[session_id] = metrics

            # Start bidirectional forwarding
            await self.forward_traffic(websocket, tcp_socket, session_id, metrics)

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"🔌 WebSocket closed for session {session_id}")
        except Exception as e:
            logger.error(f"❌ Error handling connection for session {session_id}: {e}")
            try:
                await websocket.send(json.dumps({
                    "error": "INTERNAL_ERROR",
                    "message": str(e)
                }))
            except:
                pass
        finally:
            # Cleanup
            if tcp_socket:
                try:
                    tcp_socket.close()
                    logger.debug(f"🔌 TCP socket closed for session {session_id}")
                except:
                    pass

            if session_id in active_sessions:
                del active_sessions[session_id]

            self.active_connections -= 1
            logger.info(f"🔌 Session {session_id} ended - {self.active_connections} active connections")

    async def forward_traffic(
        self,
        websocket,
        tcp_socket: socket.socket,
        session_id: str,
        metrics: dict,
    ):
        """
        Forward traffic bidirectionally between WebSocket and TCP

        WebSocket (Browser) ←→ TCP (Tunnel → VNC Server)
        """
        loop = asyncio.get_event_loop()

        async def ws_to_tcp():
            """Forward WebSocket messages to TCP socket"""
            try:
                async for message in websocket:
                    if isinstance(message, bytes):
                        # Binary data (RFB protocol)
                        await loop.sock_sendall(tcp_socket, message)
                        metrics["bytes_sent"] += len(message)
                        logger.debug(f"📤 WS→TCP: {len(message)} bytes for session {session_id}")
                    elif isinstance(message, str):
                        # Text message (control messages)
                        logger.debug(f"📤 WS→TCP text: {message[:100]}")
            except websockets.exceptions.ConnectionClosed:
                logger.debug(f"🔌 WebSocket closed (WS→TCP) for session {session_id}")
            except Exception as e:
                logger.error(f"❌ Error in WS→TCP for session {session_id}: {e}")

        async def tcp_to_ws():
            """Forward TCP socket data to WebSocket"""
            try:
                while True:
                    # Read from TCP socket (non-blocking)
                    data = await loop.sock_recv(tcp_socket, 8192)
                    if not data:
                        logger.debug(f"🔌 TCP socket closed for session {session_id}")
                        break

                    # Send to WebSocket as binary
                    await websocket.send(data)
                    metrics["bytes_received"] += len(data)
                    metrics["frames_sent"] += 1
                    logger.debug(f"📥 TCP→WS: {len(data)} bytes for session {session_id}")

            except websockets.exceptions.ConnectionClosed:
                logger.debug(f"🔌 WebSocket closed (TCP→WS) for session {session_id}")
            except Exception as e:
                logger.error(f"❌ Error in TCP→WS for session {session_id}: {e}")

        # Run both directions concurrently
        try:
            await asyncio.gather(
                ws_to_tcp(),
                tcp_to_ws(),
            )
        except Exception as e:
            logger.error(f"❌ Error in bidirectional forwarding for session {session_id}: {e}")

    async def start_server(self):
        """Start WebSocket server"""
        logger.info(f"🚀 VNC Gateway starting on {GATEWAY_HOST}:{GATEWAY_PORT}")
        logger.info(f"🔐 JWT Secret: {JWT_SECRET[:10]}...")
        logger.info(f"🌐 Backend URL: {BACKEND_URL}")
        logger.info(f"🔗 Tunnel Host: {TUNNEL_HOST}")

        async with websockets.serve(
            self.handle_connection,
            GATEWAY_HOST,
            GATEWAY_PORT,
            max_size=None,  # No message size limit (VNC can have large frames)
            ping_interval=30,  # Keep-alive ping every 30s
            ping_timeout=10,
        ):
            logger.info(f"✅ VNC Gateway listening on ws://{GATEWAY_HOST}:{GATEWAY_PORT}")
            await asyncio.Future()  # Run forever


async def main():
    """Main entry point"""
    # Configure logger
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level="INFO",
    )
    logger.add(
        "logs/vnc_gateway.log",
        rotation="100 MB",
        retention="30 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
        level="DEBUG",
    )

    logger.info("=" * 80)
    logger.info("🚀 Orizon Zero Trust Connect - VNC Gateway Service")
    logger.info("=" * 80)

    # Create VNC Gateway instance
    gateway = VNCGateway()

    # Start server
    try:
        await gateway.start_server()
    except KeyboardInterrupt:
        logger.info("🛑 VNC Gateway shutting down...")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        raise


if __name__ == "__main__":
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)

    # Run the gateway
    asyncio.run(main())
