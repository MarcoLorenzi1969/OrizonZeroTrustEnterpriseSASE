"""
Tunnel Manager - Core Tunnel Management System
For: Marco @ Syneto/Orizon

Manages all SSH and HTTPS reverse tunnels
"""

import asyncio
import uuid
from typing import Dict, List, Optional, Set
from datetime import datetime
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.tunnel import Tunnel, TunnelStatus, TunnelType
from app.models.node import Node, NodeStatus
from app.core.redis import redis_client
from app.schemas.tunnel import TunnelCreate, TunnelUpdate


class TunnelManager:
    """
    Central manager for all tunnel connections
    
    Responsibilities:
    - Track active tunnels
    - Monitor tunnel health
    - Handle tunnel creation/deletion
    - Manage tunnel routing
    - Publish tunnel events via Redis pub/sub
    """
    
    def __init__(self):
        self.active_tunnels: Dict[str, dict] = {}
        self.node_tunnels: Dict[str, Set[str]] = {}  # node_id -> set of tunnel_ids
        self._lock = asyncio.Lock()
        
    async def register_tunnel(
        self,
        db: AsyncSession,
        tunnel_id: str,
        node_id: str,
        tunnel_type: TunnelType,
        local_port: int,
        remote_port: int,
        connection_info: dict
    ) -> Optional[Tunnel]:
        """Register a new tunnel connection"""
        try:
            async with self._lock:
                # Check if tunnel already exists
                stmt = select(Tunnel).where(Tunnel.id == tunnel_id)
                result = await db.execute(stmt)
                tunnel = result.scalar_one_or_none()
                
                if not tunnel:
                    # Create new tunnel record
                    tunnel = Tunnel(
                        id=tunnel_id,
                        node_id=node_id,
                        tunnel_type=tunnel_type,
                        local_port=local_port,
                        remote_port=remote_port,
                        status=TunnelStatus.CONNECTED,
                        connected_at=datetime.utcnow()
                    )
                    db.add(tunnel)
                else:
                    # Update existing tunnel
                    tunnel.status = TunnelStatus.CONNECTED
                    tunnel.connected_at = datetime.utcnow()
                    tunnel.reconnect_count += 1
                
                await db.commit()
                await db.refresh(tunnel)
                
                # Add to active tunnels
                self.active_tunnels[tunnel_id] = {
                    "tunnel": tunnel,
                    "connection_info": connection_info,
                    "registered_at": datetime.utcnow()
                }
                
                # Track node tunnels
                if node_id not in self.node_tunnels:
                    self.node_tunnels[node_id] = set()
                self.node_tunnels[node_id].add(tunnel_id)
                
                # Update node status
                stmt = select(Node).where(Node.id == node_id)
                result = await db.execute(stmt)
                node = result.scalar_one_or_none()
                if node:
                    node.status = NodeStatus.ONLINE
                    node.last_seen = datetime.utcnow()
                    await db.commit()
                
                # Publish event via Redis
                await self._publish_tunnel_event("tunnel.connected", {
                    "tunnel_id": tunnel_id,
                    "node_id": node_id,
                    "tunnel_type": tunnel_type.value,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                logger.info(
                    f"✅ Tunnel registered: {tunnel_id} "
                    f"(Node: {node_id}, Type: {tunnel_type.value})"
                )
                
                return tunnel
                
        except Exception as e:
            logger.error(f"❌ Failed to register tunnel {tunnel_id}: {e}")
            await db.rollback()
            return None
    
    async def unregister_tunnel(
        self,
        db: AsyncSession,
        tunnel_id: str,
        reason: str = "normal_closure"
    ) -> bool:
        """Unregister a tunnel connection"""
        try:
            async with self._lock:
                if tunnel_id not in self.active_tunnels:
                    logger.warning(f"⚠️ Tunnel {tunnel_id} not in active tunnels")
                    return False
                
                tunnel_info = self.active_tunnels[tunnel_id]
                tunnel = tunnel_info["tunnel"]
                node_id = tunnel.node_id
                
                # Update tunnel status in database
                stmt = select(Tunnel).where(Tunnel.id == tunnel_id)
                result = await db.execute(stmt)
                db_tunnel = result.scalar_one_or_none()
                
                if db_tunnel:
                    db_tunnel.status = TunnelStatus.DISCONNECTED
                    db_tunnel.disconnected_at = datetime.utcnow()
                    db_tunnel.disconnect_reason = reason
                    await db.commit()
                
                # Remove from active tunnels
                del self.active_tunnels[tunnel_id]
                
                # Update node tunnels tracking
                if node_id in self.node_tunnels:
                    self.node_tunnels[node_id].discard(tunnel_id)
                    
                    # If no more tunnels for this node, mark node as offline
                    if not self.node_tunnels[node_id]:
                        del self.node_tunnels[node_id]
                        
                        stmt = select(Node).where(Node.id == node_id)
                        result = await db.execute(stmt)
                        node = result.scalar_one_or_none()
                        if node:
                            node.status = NodeStatus.OFFLINE
                            await db.commit()
                
                # Publish event via Redis
                await self._publish_tunnel_event("tunnel.disconnected", {
                    "tunnel_id": tunnel_id,
                    "node_id": node_id,
                    "reason": reason,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                logger.info(
                    f"❌ Tunnel unregistered: {tunnel_id} "
                    f"(Node: {node_id}, Reason: {reason})"
                )
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to unregister tunnel {tunnel_id}: {e}")
            return False
    
    async def get_active_tunnel(self, tunnel_id: str) -> Optional[dict]:
        """Get active tunnel information"""
        return self.active_tunnels.get(tunnel_id)
    
    async def get_node_tunnels(self, node_id: str) -> List[dict]:
        """Get all active tunnels for a specific node"""
        if node_id not in self.node_tunnels:
            return []
        
        tunnel_ids = self.node_tunnels[node_id]
        return [
            self.active_tunnels[tid]
            for tid in tunnel_ids
            if tid in self.active_tunnels
        ]
    
    async def get_all_active_tunnels(self) -> List[dict]:
        """Get all active tunnels"""
        return list(self.active_tunnels.values())
    
    async def tunnel_exists(self, tunnel_id: str) -> bool:
        """Check if tunnel is active"""
        return tunnel_id in self.active_tunnels
    
    async def get_tunnel_count(self) -> int:
        """Get total number of active tunnels"""
        return len(self.active_tunnels)
    
    async def get_node_count(self) -> int:
        """Get total number of nodes with active tunnels"""
        return len(self.node_tunnels)
    
    async def health_check(self, db: AsyncSession) -> dict:
        """Perform health check on all tunnels"""
        total = len(self.active_tunnels)
        healthy = 0
        unhealthy = []
        
        for tunnel_id, tunnel_info in self.active_tunnels.items():
            tunnel = tunnel_info["tunnel"]
            
            # Check if tunnel is still responsive
            # (implement actual health check logic here)
            is_healthy = True  # Placeholder
            
            if is_healthy:
                healthy += 1
            else:
                unhealthy.append(tunnel_id)
                # Mark tunnel as unhealthy
                tunnel.status = TunnelStatus.ERROR
        
        if unhealthy:
            await db.commit()
        
        return {
            "total_tunnels": total,
            "healthy_tunnels": healthy,
            "unhealthy_tunnels": len(unhealthy),
            "unhealthy_tunnel_ids": unhealthy,
            "nodes_connected": len(self.node_tunnels)
        }
    
    async def _publish_tunnel_event(self, event_type: str, data: dict):
        """Publish tunnel event to Redis pub/sub"""
        try:
            await redis_client.publish(
                "tunnel_events",
                {
                    "event_type": event_type,
                    "data": data
                }
            )
        except Exception as e:
            logger.error(f"Failed to publish tunnel event: {e}")


# Global tunnel manager instance
tunnel_manager = TunnelManager()
