"""
WebSocket Module - Real-time Communication
For: Marco @ Syneto/Orizon

Handles WebSocket connections for real-time updates
"""

from .manager import WebSocketManager, ws_manager
from .handlers import register_websocket_handlers

__all__ = [
    "WebSocketManager",
    "ws_manager",
    "register_websocket_handlers",
]
