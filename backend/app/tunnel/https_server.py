"""
HTTPS Reverse Tunnel Server
For: Marco @ Syneto/Orizon

Handles HTTPS reverse tunnels from agents
"""

import asyncio
import ssl
from typing import Optional, Dict
from datetime import datetime
from loguru import logger
from aiohttp import web, ClientSession
import uuid

from app.core.config import settings
from app.tunnel.manager import tunnel_manager
from app.models.tunnel import TunnelType


class HTTPSTunnelConnection:
    """Represents a single HTTPS tunnel connection"""
    
    def __init__(
        self,
        websocket: web.WebSocketResponse,
        node_id: str,
        tunnel_id: str,
        target_url: str
    ):
        self.websocket = websocket
        self.node_id = node_id
        self.tunnel_id = tunnel_id
        self.target_url = target_url
        self.connected_at = datetime.utcnow()
        self.bytes_sent = 0
        self.bytes_received = 0
    
    async def close(self):
        """Close the WebSocket connection"""
        try:
            await self.websocket.close()
        except Exception as e:
            logger.error(f"Error closing HTTPS tunnel connection: {e}")


class HTTPSReverseServer:
    """
    HTTPS Reverse Tunnel Server using WebSocket
    
    Architecture:
    - Agents connect via WebSocket with authentication
    - Server proxies HTTP/HTTPS requests through the WebSocket
    - Bidirectional streaming of request/response data
    """
    
    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
        self.active_connections: Dict[str, HTTPSTunnelConnection] = {}
        self.app = web.Application()
        self.setup_routes()
    
    def setup_routes(self):
        """Setup aiohttp routes"""
        self.app.router.add_get('/tunnel/connect', self.handle_tunnel_connect)
        self.app.router.add_get('/tunnel/health', self.handle_health)
        self.app.router.add_route('*', '/proxy/{node_id}/{path:.*}', self.handle_proxy)
    
    async def handle_health(self, request: web.Request) -> web.Response:
        """Health check endpoint"""
        return web.json_response({
            "status": "healthy",
            "active_tunnels": len(self.active_connections),
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def handle_tunnel_connect(self, request: web.Request) -> web.WebSocketResponse:
        """
        Handle WebSocket tunnel connection from agent
        
        Query params:
        - node_id: Node identifier
        - api_key: Authentication key
        - target_url: Target URL to forward requests to
        """
        ws = web.WebSocketResponse(heartbeat=30)
        await ws.prepare(request)
        
        try:
            # Get connection parameters
            node_id = request.query.get('node_id')
            api_key = request.query.get('api_key')
            target_url = request.query.get('target_url', 'http://localhost:80')
            
            if not node_id or not api_key:
                await ws.close(code=4000, message=b'Missing node_id or api_key')
                return ws
            
            # TODO: Validate api_key against database
            # For now, accept any key (SECURITY: Fix this!)
            
            # Generate tunnel ID
            tunnel_id = f"https_{node_id}_{uuid.uuid4().hex[:8]}"
            
            logger.info(
                f"🔌 HTTPS tunnel connection from node: {node_id} "
                f"(Tunnel: {tunnel_id})"
            )
            
            # Register tunnel
            async with self.db_session_factory() as db:
                tunnel = await tunnel_manager.register_tunnel(
                    db=db,
                    tunnel_id=tunnel_id,
                    node_id=node_id,
                    tunnel_type=TunnelType.HTTPS,
                    local_port=settings.TUNNEL_HTTPS_PORT,
                    remote_port=0,  # Dynamic
                    connection_info={
                        "target_url": target_url,
                        "node_id": node_id
                    }
                )
                
                if not tunnel:
                    await ws.close(code=4001, message=b'Failed to register tunnel')
                    return ws
            
            # Create connection object
            conn = HTTPSTunnelConnection(
                websocket=ws,
                node_id=node_id,
                tunnel_id=tunnel_id,
                target_url=target_url
            )
            self.active_connections[tunnel_id] = conn
            
            # Send connection confirmation
            await ws.send_json({
                "type": "tunnel_established",
                "tunnel_id": tunnel_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Keep connection alive and handle messages
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    data = msg.json()
                    await self._handle_tunnel_message(tunnel_id, data)
                    
                elif msg.type == web.WSMsgType.BINARY:
                    # Handle binary data
                    conn.bytes_received += len(msg.data)
                    
                elif msg.type == web.WSMsgType.ERROR:
                    logger.error(
                        f"WebSocket error in tunnel {tunnel_id}: "
                        f"{ws.exception()}"
                    )
                    break
            
        except Exception as e:
            logger.error(f"Error in HTTPS tunnel connection: {e}")
            
        finally:
            # Cleanup
            if tunnel_id in self.active_connections:
                conn = self.active_connections[tunnel_id]
                await conn.close()
                del self.active_connections[tunnel_id]
                
                # Unregister tunnel
                async with self.db_session_factory() as db:
                    await tunnel_manager.unregister_tunnel(
                        db=db,
                        tunnel_id=tunnel_id,
                        reason="connection_closed"
                    )
                
                logger.info(f"❌ HTTPS tunnel closed: {tunnel_id}")
        
        return ws
    
    async def _handle_tunnel_message(self, tunnel_id: str, data: dict):
        """Handle message from tunnel agent"""
        msg_type = data.get('type')
        
        if msg_type == 'heartbeat':
            # Respond to heartbeat
            conn = self.active_connections.get(tunnel_id)
            if conn:
                await conn.websocket.send_json({
                    "type": "heartbeat_ack",
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        elif msg_type == 'response':
            # Handle HTTP response from agent
            # (Response to a proxied request)
            pass  # TODO: Implement response handling
        
        else:
            logger.warning(f"Unknown message type from tunnel {tunnel_id}: {msg_type}")
    
    async def handle_proxy(self, request: web.Request) -> web.Response:
        """
        Proxy HTTP request through tunnel
        
        Path format: /proxy/{node_id}/{path}
        """
        node_id = request.match_info['node_id']
        path = request.match_info['path']
        
        # Find active tunnel for this node
        tunnel_id = None
        for tid, conn in self.active_connections.items():
            if conn.node_id == node_id:
                tunnel_id = tid
                break
        
        if not tunnel_id:
            return web.json_response(
                {"error": f"No active tunnel for node: {node_id}"},
                status=404
            )
        
        conn = self.active_connections[tunnel_id]
        
        try:
            # Build request data to send through tunnel
            request_data = {
                "type": "request",
                "request_id": uuid.uuid4().hex,
                "method": request.method,
                "path": f"/{path}",
                "headers": dict(request.headers),
                "query": dict(request.query),
            }
            
            # Add body for POST/PUT/PATCH
            if request.method in ['POST', 'PUT', 'PATCH']:
                request_data["body"] = (await request.read()).decode('utf-8')
            
            # Send request through WebSocket
            await conn.websocket.send_json(request_data)
            conn.bytes_sent += len(str(request_data))
            
            # Wait for response (with timeout)
            # TODO: Implement proper request/response matching
            # For now, return a placeholder
            
            return web.json_response({
                "message": "Request forwarded through tunnel",
                "tunnel_id": tunnel_id,
                "node_id": node_id
            })
            
        except Exception as e:
            logger.error(f"Error proxying request through tunnel: {e}")
            return web.json_response(
                {"error": "Failed to proxy request"},
                status=500
            )
    
    async def get_active_tunnels(self) -> Dict[str, dict]:
        """Get all active HTTPS tunnels"""
        return {
            tid: {
                "tunnel_id": conn.tunnel_id,
                "node_id": conn.node_id,
                "target_url": conn.target_url,
                "connected_at": conn.connected_at.isoformat(),
                "bytes_sent": conn.bytes_sent,
                "bytes_received": conn.bytes_received
            }
            for tid, conn in self.active_connections.items()
        }


class HTTPSReverseServerManager:
    """Manager for HTTPS Reverse Server"""
    
    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
        self.https_server: Optional[HTTPSReverseServer] = None
        self.runner: Optional[web.AppRunner] = None
    
    async def start(self):
        """Start HTTPS reverse tunnel server"""
        try:
            logger.info(
                f"🚀 Starting HTTPS Reverse Server on port "
                f"{settings.TUNNEL_HTTPS_PORT}"
            )
            
            # Create server instance
            self.https_server = HTTPSReverseServer(self.db_session_factory)
            
            # Setup SSL context (optional, for HTTPS)
            # ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            # ssl_context.load_cert_chain('cert.pem', 'key.pem')
            
            # Start aiohttp server
            self.runner = web.AppRunner(self.https_server.app)
            await self.runner.setup()
            
            site = web.TCPSite(
                self.runner,
                host='0.0.0.0',
                port=settings.TUNNEL_HTTPS_PORT,
                # ssl_context=ssl_context  # Uncomment for HTTPS
            )
            
            await site.start()
            
            logger.info(
                f"✅ HTTPS Reverse Server started on "
                f"0.0.0.0:{settings.TUNNEL_HTTPS_PORT}"
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to start HTTPS Reverse Server: {e}")
            raise
    
    async def stop(self):
        """Stop HTTPS reverse tunnel server"""
        if self.runner:
            logger.info("⏹️ Stopping HTTPS Reverse Server...")
            await self.runner.cleanup()
            logger.info("✅ HTTPS Reverse Server stopped")
    
    async def get_active_tunnels(self) -> Dict[str, dict]:
        """Get all active HTTPS tunnels"""
        if self.https_server:
            return await self.https_server.get_active_tunnels()
        return {}


# Global HTTPS server manager instance
https_server_manager: Optional[HTTPSReverseServerManager] = None


def init_https_server(db_session_factory):
    """Initialize HTTPS server manager"""
    global https_server_manager
    https_server_manager = HTTPSReverseServerManager(db_session_factory)
    return https_server_manager
