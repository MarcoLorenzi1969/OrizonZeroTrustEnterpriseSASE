"""
Orizon Zero Trust Connect - Health Check API
System health and status endpoints

Author: Marco Lorenzi - Syneto Orizon
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime
import psutil

from app.core.database import get_db
from app.core.redis_client import get_redis, RedisClient
from app.core.config import settings

router = APIRouter()


@router.get("")
@router.get("/")
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis)
):
    """
    Basic health check endpoint
    Returns 200 if service is healthy
    """
    # Check database
    try:
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    # Check Redis
    try:
        redis_healthy = await redis.ping()
        redis_status = "healthy" if redis_healthy else "unhealthy"
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.APP_VERSION,
        "environment": settings.ENV,
        "services": {
            "database": db_status,
            "redis": redis_status,
        }
    }


@router.get("/detailed")
async def detailed_health_check(
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis)
):
    """
    Detailed health check with system metrics
    """
    # Database check
    try:
        await db.execute(text("SELECT 1"))
        db_status = {
            "status": "healthy",
            "url": settings.DATABASE_URL.split("@")[1] if "@" in settings.DATABASE_URL else "hidden"
        }
    except Exception as e:
        db_status = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Redis check
    try:
        redis_healthy = await redis.ping()
        redis_status = {
            "status": "healthy" if redis_healthy else "unhealthy",
            "url": settings.REDIS_URL.split("@")[1] if "@" in settings.REDIS_URL else "hidden"
        }
    except Exception as e:
        redis_status = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # System metrics
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "application": {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENV,
            "debug": settings.DEBUG,
        },
        "services": {
            "database": db_status,
            "redis": redis_status,
        },
        "system": {
            "cpu_usage_percent": cpu_percent,
            "memory": {
                "total_mb": round(memory.total / (1024 * 1024), 2),
                "available_mb": round(memory.available / (1024 * 1024), 2),
                "used_mb": round(memory.used / (1024 * 1024), 2),
                "percent": memory.percent,
            },
            "disk": {
                "total_gb": round(disk.total / (1024 ** 3), 2),
                "used_gb": round(disk.used / (1024 ** 3), 2),
                "free_gb": round(disk.free / (1024 ** 3), 2),
                "percent": disk.percent,
            },
        }
    }


@router.get("/liveness")
async def liveness():
    """
    Kubernetes liveness probe
    Returns 200 if service is running
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


@router.get("/readiness")
async def readiness(
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis)
):
    """
    Kubernetes readiness probe
    Returns 200 if service is ready to accept traffic
    """
    # Check critical dependencies
    try:
        await db.execute(text("SELECT 1"))
        await redis.ping()
        
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "not_ready",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }, 503
