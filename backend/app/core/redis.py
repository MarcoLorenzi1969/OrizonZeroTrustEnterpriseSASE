"""
Orizon Zero Trust Connect - Redis Client
For: Marco @ Syneto/Orizon
"""

import json
from typing import Optional, Any
from redis import asyncio as aioredis
from app.core.config import settings
from loguru import logger


class RedisClient:
    """Async Redis client wrapper"""
    
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
    
    async def connect(self) -> None:
        """Connect to Redis"""
        try:
            self.redis = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
            )
            await self.redis.ping()
            logger.info("✅ Redis connected successfully")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
            logger.info("Redis disconnected")
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        if not self.redis:
            return None
        return await self.redis.get(key)
    
    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None
    ) -> bool:
        """Set key-value pair with optional expiration"""
        if not self.redis:
            return False
        
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        
        if expire:
            return await self.redis.setex(key, expire, value)
        return await self.redis.set(key, value)
    
    async def delete(self, key: str) -> bool:
        """Delete key"""
        if not self.redis:
            return False
        result = await self.redis.delete(key)
        return result > 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.redis:
            return False
        return await self.redis.exists(key) > 0
    
    async def incr(self, key: str) -> int:
        """Increment counter"""
        if not self.redis:
            return 0
        return await self.redis.incr(key)
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key"""
        if not self.redis:
            return False
        return await self.redis.expire(key, seconds)
    
    async def publish(self, channel: str, message: Any) -> int:
        """Publish message to channel"""
        if not self.redis:
            return 0
        
        if isinstance(message, (dict, list)):
            message = json.dumps(message)
        
        return await self.redis.publish(channel, message)
    
    async def subscribe(self, channel: str):
        """Subscribe to channel"""
        if not self.redis:
            return None
        
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel)
        return pubsub


# Global Redis client instance
redis_client = RedisClient()


async def get_redis() -> RedisClient:
    """Dependency for getting Redis client"""
    return redis_client
