"""
Orizon Zero Trust Connect - MongoDB Client
For: Marco @ Syneto/Orizon
MongoDB for logs, audit trail, and time-series data
"""

from typing import Optional, List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from datetime import datetime
from app.core.config import settings
from loguru import logger


class MongoDBClient:
    """Async MongoDB client wrapper"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
    
    async def connect(self) -> None:
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                serverSelectionTimeoutMS=5000,
            )
            self.db = self.client[settings.MONGODB_DB]
            
            # Test connection
            await self.client.server_info()
            logger.info("✅ MongoDB connected successfully")
            
            # Create indexes
            await self._create_indexes()
            
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            logger.info("MongoDB disconnected")
    
    async def _create_indexes(self) -> None:
        """Create necessary indexes"""
        # Audit logs indexes
        await self.db.audit_logs.create_index([("timestamp", -1)])
        await self.db.audit_logs.create_index([("user_id", 1)])
        await self.db.audit_logs.create_index([("action", 1)])
        
        # System logs indexes
        await self.db.system_logs.create_index([("timestamp", -1)])
        await self.db.system_logs.create_index([("level", 1)])
        await self.db.system_logs.create_index([("node_id", 1)])
        
        # Tunnel logs indexes
        await self.db.tunnel_logs.create_index([("timestamp", -1)])
        await self.db.tunnel_logs.create_index([("tunnel_id", 1)])
        await self.db.tunnel_logs.create_index([("status", 1)])
    
    async def log_audit(
        self,
        user_id: str,
        action: str,
        resource: str,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> str:
        """Log audit event"""
        doc = {
            "timestamp": datetime.utcnow(),
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "details": details or {},
            "ip_address": ip_address,
        }
        result = await self.db.audit_logs.insert_one(doc)
        return str(result.inserted_id)
    
    async def log_system(
        self,
        level: str,
        message: str,
        node_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Log system event"""
        doc = {
            "timestamp": datetime.utcnow(),
            "level": level,
            "message": message,
            "node_id": node_id,
            "details": details or {},
        }
        result = await self.db.system_logs.insert_one(doc)
        return str(result.inserted_id)
    
    async def log_tunnel(
        self,
        tunnel_id: str,
        status: str,
        event: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Log tunnel event"""
        doc = {
            "timestamp": datetime.utcnow(),
            "tunnel_id": tunnel_id,
            "status": status,
            "event": event,
            "details": details or {},
        }
        result = await self.db.tunnel_logs.insert_one(doc)
        return str(result.inserted_id)
    
    async def get_audit_logs(
        self,
        user_id: Optional[str] = None,
        limit: int = 100,
        skip: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get audit logs with filtering"""
        query = {}
        if user_id:
            query["user_id"] = user_id
        
        cursor = self.db.audit_logs.find(query).sort("timestamp", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
    
    async def get_system_logs(
        self,
        level: Optional[str] = None,
        node_id: Optional[str] = None,
        limit: int = 100,
        skip: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get system logs with filtering"""
        query = {}
        if level:
            query["level"] = level
        if node_id:
            query["node_id"] = node_id
        
        cursor = self.db.system_logs.find(query).sort("timestamp", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
    
    async def get_tunnel_logs(
        self,
        tunnel_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        skip: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get tunnel logs with filtering"""
        query = {}
        if tunnel_id:
            query["tunnel_id"] = tunnel_id
        if status:
            query["status"] = status
        
        cursor = self.db.tunnel_logs.find(query).sort("timestamp", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)


# Global MongoDB client instance
mongodb_client = MongoDBClient()


async def get_mongodb() -> MongoDBClient:
    """Dependency for getting MongoDB client"""
    return mongodb_client
