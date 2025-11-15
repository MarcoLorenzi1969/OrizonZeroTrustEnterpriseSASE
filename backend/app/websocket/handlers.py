"""
WebSocket Handlers
For: Marco @ Syneto/Orizon

Handles different types of WebSocket messages
"""

from typing import Dict, Any
from loguru import logger

from app.websocket.manager import ws_manager


async def handle_ping(connection_id: str, data: Dict[str, Any]):
    """Handle ping message"""
    await ws_manager.send_personal_message(
        connection_id,
        {
            "type": "pong",
            "timestamp": data.get("timestamp")
        }
    )


async def handle_subscribe(connection_id: str, data: Dict[str, Any]):
    """Handle channel subscription"""
    channel = data.get("channel")
    if channel:
        await ws_manager.subscribe(connection_id, channel)
        await ws_manager.send_personal_message(
            connection_id,
            {
                "type": "subscribed",
                "channel": channel
            }
        )


async def handle_unsubscribe(connection_id: str, data: Dict[str, Any]):
    """Handle channel unsubscription"""
    channel = data.get("channel")
    if channel:
        await ws_manager.unsubscribe(connection_id, channel)
        await ws_manager.send_personal_message(
            connection_id,
            {
                "type": "unsubscribed",
                "channel": channel
            }
        )


async def handle_get_status(connection_id: str, data: Dict[str, Any]):
    """Handle status request"""
    status = {
        "type": "status",
        "connections": await ws_manager.get_connection_count(),
        "users": await ws_manager.get_user_count()
    }
    
    await ws_manager.send_personal_message(connection_id, status)


# Message handlers registry
MESSAGE_HANDLERS = {
    "ping": handle_ping,
    "subscribe": handle_subscribe,
    "unsubscribe": handle_unsubscribe,
    "get_status": handle_get_status,
}


async def handle_websocket_message(
    connection_id: str,
    message: Dict[str, Any]
):
    """Route WebSocket message to appropriate handler"""
    msg_type = message.get("type")
    
    if not msg_type:
        logger.warning(f"Received message without type from {connection_id}")
        return
    
    handler = MESSAGE_HANDLERS.get(msg_type)
    
    if handler:
        try:
            await handler(connection_id, message)
        except Exception as e:
            logger.error(
                f"Error handling message type '{msg_type}' "
                f"from {connection_id}: {e}"
            )
    else:
        logger.warning(
            f"Unknown message type '{msg_type}' from {connection_id}"
        )


def register_websocket_handlers(custom_handlers: Dict[str, Any] = None):
    """Register custom WebSocket handlers"""
    if custom_handlers:
        MESSAGE_HANDLERS.update(custom_handlers)
        logger.info(f"Registered custom WebSocket handlers: {list(custom_handlers.keys())}")
