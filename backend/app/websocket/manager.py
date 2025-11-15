"""
WebSocket Manager - Real-time Communication Manager
For: Marco @ Syneto/Orizon

Manages WebSocket connections for real-time dashboard updates
"""

import asyncio
import json
from typing import Dict, Set, Optional, List
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

from app.core.redis import redis_client
from app.models.user import UserRole


class WebSocketConnection:
    """Represents a single WebSocket connection"""
    
    def __init__(
        self,
        websocket: WebSocket,
        user_id: str,
        user_role: UserRole,
        connection_id: str
    ):
        self.websocket = websocket
        self.user_id = user_id
        self.user_role = user_role
        self.connection_id = connection_id
        self.connected_at = datetime.utcnow()
        self.subscribed_channels: Set[str] = set()
    
    async def send_json(self, data: dict):
        """Send JSON data through WebSocket"""
        try:
            await self.websocket.send_json(data)
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")
    
    async def send_text(self, message: str):
        """Send text message through WebSocket"""
        try:
            await self.websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending WebSocket text: {e}")
    
    async def close(self, code: int = 1000):
        """Close WebSocket connection"""
        try:
            await self.websocket.close(code=code)
        except Exception as e:
            logger.error(f"Error closing WebSocket: {e}")


class WebSocketManager:
    """
    Manages all WebSocket connections
    
    Features:
    - Connection management
    - Broadcasting to all/specific users
    - Channel-based pub/sub
    - Role-based message filtering
    - Redis integration for multi-instance support
    """
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocketConnection] = {}
        self.user_connections: Dict[str, Set[str]] = {}  # user_id -> connection_ids
        self.channel_subscribers: Dict[str, Set[str]] = {}  # channel -> connection_ids
        self._lock = asyncio.Lock()
        self._redis_listener_task: Optional[asyncio.Task] = None
    
    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        user_role: UserRole,
        connection_id: str
    ) -> WebSocketConnection:
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        
        async with self._lock:
            # Create connection object
            conn = WebSocketConnection(
                websocket=websocket,
                user_id=user_id,
                user_role=user_role,
                connection_id=connection_id
            )
            
            # Register connection
            self.active_connections[connection_id] = conn
            
            # Track user connections
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)
            
            logger.info(
                f"✅ WebSocket connected: {connection_id} "
                f"(User: {user_id}, Role: {user_role.value})"
            )
            
            # Send connection confirmation
            await conn.send_json({
                "type": "connection_established",
                "connection_id": connection_id,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return conn
    
    async def disconnect(self, connection_id: str):
        """Disconnect and cleanup WebSocket connection"""
        async with self._lock:
            if connection_id not in self.active_connections:
                return
            
            conn = self.active_connections[connection_id]
            user_id = conn.user_id
            
            # Unsubscribe from all channels
            for channel in conn.subscribed_channels:
                if channel in self.channel_subscribers:
                    self.channel_subscribers[channel].discard(connection_id)
                    if not self.channel_subscribers[channel]:
                        del self.channel_subscribers[channel]
            
            # Remove from user connections
            if user_id in self.user_connections:
                self.user_connections[user_id].discard(connection_id)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            
            # Close connection
            await conn.close()
            
            # Remove from active connections
            del self.active_connections[connection_id]
            
            logger.info(f"❌ WebSocket disconnected: {connection_id}")
    
    async def subscribe(self, connection_id: str, channel: str):
        """Subscribe connection to a channel"""
        async with self._lock:
            if connection_id not in self.active_connections:
                return
            
            conn = self.active_connections[connection_id]
            conn.subscribed_channels.add(channel)
            
            if channel not in self.channel_subscribers:
                self.channel_subscribers[channel] = set()
            self.channel_subscribers[channel].add(connection_id)
            
            logger.info(f"📢 Connection {connection_id} subscribed to {channel}")
    
    async def unsubscribe(self, connection_id: str, channel: str):
        """Unsubscribe connection from a channel"""
        async with self._lock:
            if connection_id in self.active_connections:
                conn = self.active_connections[connection_id]
                conn.subscribed_channels.discard(channel)
            
            if channel in self.channel_subscribers:
                self.channel_subscribers[channel].discard(connection_id)
                if not self.channel_subscribers[channel]:
                    del self.channel_subscribers[channel]
            
            logger.info(f"🔕 Connection {connection_id} unsubscribed from {channel}")
    
    async def send_personal_message(
        self,
        connection_id: str,
        message: dict
    ):
        """Send message to a specific connection"""
        conn = self.active_connections.get(connection_id)
        if conn:
            await conn.send_json(message)
    
    async def send_user_message(
        self,
        user_id: str,
        message: dict
    ):
        """Send message to all connections of a specific user"""
        connection_ids = self.user_connections.get(user_id, set())
        
        tasks = []
        for conn_id in connection_ids:
            conn = self.active_connections.get(conn_id)
            if conn:
                tasks.append(conn.send_json(message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def broadcast(
        self,
        message: dict,
        exclude_connection_id: Optional[str] = None
    ):
        """Broadcast message to all active connections"""
        tasks = []
        
        for conn_id, conn in self.active_connections.items():
            if conn_id != exclude_connection_id:
                tasks.append(conn.send_json(message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def broadcast_to_channel(
        self,
        channel: str,
        message: dict
    ):
        """Broadcast message to all connections subscribed to a channel"""
        connection_ids = self.channel_subscribers.get(channel, set())
        
        tasks = []
        for conn_id in connection_ids:
            conn = self.active_connections.get(conn_id)
            if conn:
                tasks.append(conn.send_json(message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def broadcast_to_role(
        self,
        role: UserRole,
        message: dict
    ):
        """Broadcast message to all users with specific role or higher"""
        role_hierarchy = {
            UserRole.SUPERUSER: 4,
            UserRole.SUPER_ADMIN: 3,
            UserRole.ADMIN: 2,
            UserRole.USER: 1
        }
        
        target_level = role_hierarchy.get(role, 0)
        
        tasks = []
        for conn in self.active_connections.values():
            conn_level = role_hierarchy.get(conn.user_role, 0)
            if conn_level >= target_level:
                tasks.append(conn.send_json(message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def get_user_connections(self, user_id: str) -> List[str]:
        """Get all active connection IDs for a user"""
        return list(self.user_connections.get(user_id, set()))
    
    async def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return len(self.active_connections)
    
    async def get_user_count(self) -> int:
        """Get number of unique users connected"""
        return len(self.user_connections)
    
    async def start_redis_listener(self):
        """Start listening to Redis pub/sub for cross-instance messaging"""
        self._redis_listener_task = asyncio.create_task(
            self._redis_listener_loop()
        )
        logger.info("🔊 Started Redis pub/sub listener for WebSocket")
    
    async def stop_redis_listener(self):
        """Stop Redis pub/sub listener"""
        if self._redis_listener_task:
            self._redis_listener_task.cancel()
            try:
                await self._redis_listener_task
            except asyncio.CancelledError:
                pass
            logger.info("🔇 Stopped Redis pub/sub listener")
    
    async def _redis_listener_loop(self):
        """Listen to Redis pub/sub channels"""
        try:
            # Subscribe to broadcast channels
            channels = [
                "websocket_broadcast",
                "tunnel_events",
                "node_events",
                "system_events"
            ]
            
            pubsub = redis_client.redis.pubsub()
            await pubsub.subscribe(*channels)
            
            logger.info(f"📡 Subscribed to Redis channels: {channels}")
            
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        channel = message["channel"]
                        
                        # Broadcast to appropriate WebSocket channel
                        await self.broadcast_to_channel(channel, data)
                        
                    except Exception as e:
                        logger.error(f"Error processing Redis message: {e}")
                        
        except asyncio.CancelledError:
            logger.info("Redis listener cancelled")
        except Exception as e:
            logger.error(f"Error in Redis listener: {e}")


# Global WebSocket manager instance
ws_manager = WebSocketManager()
