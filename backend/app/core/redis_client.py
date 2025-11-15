"""
Orizon Zero Trust Connect - Redis Client
Async Redis client for caching and session management

Author: Marco Lorenzi - Syneto Orizon
"""

import redis.asyncio as aioredis
from typing import Optional, Any
import json
import logging
from datetime import timedelta

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Async Redis client wrapper"""
    
    def __init__(self):
        self._client: Optional[aioredis.Redis] = None
        self._session_client: Optional[aioredis.Redis] = None
        self._cache_client: Optional[aioredis.Redis] = None
    
    async def connect(self):
        """Connect to Redis"""
        try:
            # Main client
            self._client = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            
            # Session store (DB 1)
            session_url = settings.REDIS_URL.rsplit("/", 1)[0] + f"/{settings.REDIS_SESSION_DB}"
            self._session_client = await aioredis.from_url(
                session_url,
                encoding="utf-8",
                decode_responses=True
            )
            
            # Cache store (DB 2)
            cache_url = settings.REDIS_URL.rsplit("/", 1)[0] + f"/{settings.REDIS_CACHE_DB}"
            self._cache_client = await aioredis.from_url(
                cache_url,
                encoding="utf-8",
                decode_responses=True
            )
            
            # Test connection
            await self._client.ping()
            logger.info("✅ Redis connected successfully")
            
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            raise
    
    async def close(self):
        """Close Redis connection"""
        if self._client:
            await self._client.close()
        if self._session_client:
            await self._session_client.close()
        if self._cache_client:
            await self._cache_client.close()
        logger.info("Redis connections closed")
    
    async def ping(self) -> bool:
        """Check Redis connection"""
        try:
            return await self._client.ping()
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False
    
    # ========================================
    # General Key-Value Operations
    # ========================================
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """Set key-value pair"""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            if expire:
                return await self._client.setex(key, expire, value)
            else:
                return await self._client.set(key, value)
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value by key"""
        try:
            value = await self._client.get(key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        """Delete key"""
        try:
            return await self._client.delete(key) > 0
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return await self._client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set key expiration"""
        try:
            return await self._client.expire(key, seconds)
        except Exception as e:
            logger.error(f"Redis expire error: {e}")
            return False
    
    # ========================================
    # Cache Operations
    # ========================================
    
    async def cache_set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set cache value with TTL"""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            return await self._cache_client.setex(key, ttl, value)
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def cache_get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        try:
            value = await self._cache_client.get(key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def cache_delete(self, key: str) -> bool:
        """Delete cached value"""
        try:
            return await self._cache_client.delete(key) > 0
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    async def cache_clear(self, pattern: str = "*") -> int:
        """Clear cache by pattern"""
        try:
            keys = await self._cache_client.keys(pattern)
            if keys:
                return await self._cache_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return 0
    
    # ========================================
    # Session Operations
    # ========================================
    
    async def session_set(self, session_id: str, data: dict, ttl: int = 1800) -> bool:
        """Set session data"""
        try:
            return await self._session_client.setex(
                f"session:{session_id}",
                ttl,
                json.dumps(data)
            )
        except Exception as e:
            logger.error(f"Session set error: {e}")
            return False
    
    async def session_get(self, session_id: str) -> Optional[dict]:
        """Get session data"""
        try:
            data = await self._session_client.get(f"session:{session_id}")
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Session get error: {e}")
            return None
    
    async def session_delete(self, session_id: str) -> bool:
        """Delete session"""
        try:
            return await self._session_client.delete(f"session:{session_id}") > 0
        except Exception as e:
            logger.error(f"Session delete error: {e}")
            return False
    
    async def session_refresh(self, session_id: str, ttl: int = 1800) -> bool:
        """Refresh session TTL"""
        try:
            return await self._session_client.expire(f"session:{session_id}", ttl)
        except Exception as e:
            logger.error(f"Session refresh error: {e}")
            return False
    
    # ========================================
    # Pub/Sub Operations
    # ========================================
    
    async def publish(self, channel: str, message: dict) -> int:
        """Publish message to channel"""
        try:
            return await self._client.publish(channel, json.dumps(message))
        except Exception as e:
            logger.error(f"Publish error: {e}")
            return 0
    
    async def subscribe(self, channel: str):
        """Subscribe to channel"""
        try:
            pubsub = self._client.pubsub()
            await pubsub.subscribe(channel)
            return pubsub
        except Exception as e:
            logger.error(f"Subscribe error: {e}")
            return None
    
    # ========================================
    # Hash Operations
    # ========================================
    
    async def hset(self, name: str, key: str, value: Any) -> bool:
        """Set hash field"""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            return await self._client.hset(name, key, value) > 0
        except Exception as e:
            logger.error(f"Hash set error: {e}")
            return False
    
    async def hget(self, name: str, key: str) -> Optional[Any]:
        """Get hash field"""
        try:
            value = await self._client.hget(name, key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except Exception as e:
            logger.error(f"Hash get error: {e}")
            return None
    
    async def hgetall(self, name: str) -> dict:
        """Get all hash fields"""
        try:
            data = await self._client.hgetall(name)
            result = {}
            for key, value in data.items():
                try:
                    result[key] = json.loads(value)
                except json.JSONDecodeError:
                    result[key] = value
            return result
        except Exception as e:
            logger.error(f"Hash getall error: {e}")
            return {}
    
    async def hdel(self, name: str, *keys: str) -> int:
        """Delete hash fields"""
        try:
            return await self._client.hdel(name, *keys)
        except Exception as e:
            logger.error(f"Hash delete error: {e}")
            return 0


# Global Redis client instance
redis_client = RedisClient()


async def get_redis() -> RedisClient:
    """Dependency for getting Redis client"""
    if not redis_client._client:
        await redis_client.connect()
    return redis_client
