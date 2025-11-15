"""
Orizon Zero Trust Connect - Core Module
For: Marco @ Syneto/Orizon
"""

from app.core.config import settings
from app.core.database import get_db, init_db, close_db
from app.core.redis import redis_client, get_redis
from app.core.mongodb import mongodb_client, get_mongodb

__all__ = [
    "settings",
    "get_db",
    "init_db",
    "close_db",
    "redis_client",
    "get_redis",
    "mongodb_client",
    "get_mongodb",
]
