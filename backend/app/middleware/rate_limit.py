"""
Orizon Zero Trust Connect - Rate Limiting Middleware
For: Marco @ Syneto/Orizon

Advanced rate limiting with Redis backend and configurable limits
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger
import hashlib
from typing import Optional

from app.core.redis import redis_client
from app.core.config import settings


class CustomKeyFunc:
    """
    Custom key function for rate limiting
    Supports user-based and IP-based rate limiting
    """

    @staticmethod
    async def get_identifier(request: Request) -> str:
        """
        Get identifier for rate limiting

        Priority:
        1. User ID from JWT (if authenticated)
        2. API Key (if present)
        3. IP address (fallback)

        Args:
            request: FastAPI request

        Returns:
            Unique identifier string
        """
        # Try to get user from request state (set by auth middleware)
        if hasattr(request.state, "user"):
            user_id = getattr(request.state.user, "id", None)
            if user_id:
                return f"user:{user_id}"

        # Try to get API key from header
        api_key = request.headers.get("X-API-Key")
        if api_key:
            # Hash API key for privacy
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
            return f"apikey:{key_hash}"

        # Fallback to IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Get first IP in X-Forwarded-For chain
            ip = forwarded_for.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        return f"ip:{ip}"


def get_rate_limit_key(request: Request) -> str:
    """Synchronous wrapper for CustomKeyFunc.get_identifier"""
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If event loop is running, we can't use run_until_complete
            # Fall back to IP-based limiting
            return get_remote_address(request)
        else:
            return loop.run_until_complete(CustomKeyFunc.get_identifier(request))
    except Exception as e:
        logger.error(f"Error getting rate limit key: {e}")
        return get_remote_address(request)


# Initialize limiter with Redis backend
limiter = Limiter(
    key_func=get_rate_limit_key,
    storage_uri=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/1",
    default_limits=["1000/hour", "100/minute"],  # Global default limits
    headers_enabled=True,  # Add rate limit headers to responses
    swallow_errors=True  # Continue on Redis errors (fail open)
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Custom rate limiting middleware with enhanced features

    Features:
    - Dynamic rate limits based on user role
    - Endpoint-specific rate limits
    - Rate limit headers in response
    - Audit logging for rate limit violations
    """

    # Rate limits by user role (requests per minute)
    ROLE_RATE_LIMITS = {
        "superuser": 1000,
        "super_admin": 500,
        "admin": 200,
        "user": 100,
        "anonymous": 60
    }

    # Special rate limits for sensitive endpoints
    ENDPOINT_RATE_LIMITS = {
        "/api/v1/auth/login": "10/minute",
        "/api/v1/auth/register": "5/minute",
        "/api/v1/auth/password-reset": "3/minute",
        "/api/v1/auth/2fa/verify": "10/minute",
        "/api/v1/tunnels": "20/minute",
        "/api/v1/nodes": "50/minute"
    }

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""

        # Skip rate limiting for health checks and metrics
        if request.url.path in ["/health", "/metrics", "/api/docs", "/api/openapi.json"]:
            return await call_next(request)

        try:
            # Get identifier for rate limiting
            identifier = await CustomKeyFunc.get_identifier(request)

            # Get user role (if authenticated)
            user_role = "anonymous"
            if hasattr(request.state, "user"):
                user_role = getattr(request.state.user, "role", "user").lower()

            # Check rate limit
            is_allowed, remaining, reset_time = await self._check_rate_limit(
                identifier=identifier,
                endpoint=request.url.path,
                user_role=user_role
            )

            # Proceed with request
            response = await call_next(request)

            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(self.ROLE_RATE_LIMITS.get(user_role, 100))
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset_time)

            return response

        except RateLimitExceeded as e:
            logger.warning(
                f"⚠️ Rate limit exceeded: {identifier} on {request.url.path}"
            )

            # Log to audit (if available)
            await self._log_rate_limit_violation(request, identifier)

            # Return 429 Too Many Requests
            return Response(
                content='{"detail": "Rate limit exceeded. Please try again later."}',
                status_code=429,
                media_type="application/json",
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": "100",
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time)
                }
            )

        except Exception as e:
            logger.error(f"❌ Error in rate limiting middleware: {e}")
            # Fail open - allow request to proceed
            return await call_next(request)

    async def _check_rate_limit(
        self,
        identifier: str,
        endpoint: str,
        user_role: str
    ) -> tuple[bool, int, int]:
        """
        Check if request is within rate limit

        Args:
            identifier: Unique identifier (user ID, API key, or IP)
            endpoint: Request endpoint
            user_role: User role

        Returns:
            Tuple of (is_allowed, remaining_requests, reset_timestamp)
        """
        try:
            # Get rate limit for this endpoint/role
            if endpoint in self.ENDPOINT_RATE_LIMITS:
                # Use endpoint-specific limit
                limit_str = self.ENDPOINT_RATE_LIMITS[endpoint]
                limit, window = self._parse_limit_string(limit_str)
            else:
                # Use role-based limit
                limit = self.ROLE_RATE_LIMITS.get(user_role, 100)
                window = 60  # 1 minute

            # Build Redis key
            redis_key = f"rate_limit:{identifier}:{endpoint}:{window}"

            # Get current count
            current = await redis_client.get(redis_key)

            if current is None:
                # First request in window
                await redis_client.set_with_expiry(redis_key, "1", expiry=window)
                remaining = limit - 1
                reset_time = int(time.time()) + window
                return True, remaining, reset_time

            current = int(current)

            # Check if within limit
            if current >= limit:
                # Rate limit exceeded
                ttl = await redis_client.ttl(redis_key)
                reset_time = int(time.time()) + ttl
                return False, 0, reset_time

            # Increment counter
            await redis_client.increment(redis_key)
            remaining = limit - current - 1
            ttl = await redis_client.ttl(redis_key)
            reset_time = int(time.time()) + ttl

            return True, remaining, reset_time

        except Exception as e:
            logger.error(f"❌ Error checking rate limit: {e}")
            # Fail open - allow request
            return True, 100, int(time.time()) + 60

    def _parse_limit_string(self, limit_str: str) -> tuple[int, int]:
        """
        Parse limit string like "10/minute" to (count, seconds)

        Args:
            limit_str: Limit string (e.g., "10/minute", "100/hour")

        Returns:
            Tuple of (count, window_seconds)
        """
        count, period = limit_str.split("/")
        count = int(count)

        period_map = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400
        }

        window = period_map.get(period, 60)
        return count, window

    async def _log_rate_limit_violation(self, request: Request, identifier: str):
        """Log rate limit violation to audit system"""
        try:
            # Import here to avoid circular dependency
            from app.services.audit_service import audit_service
            from app.models.audit_log import AuditAction, AuditSeverity
            from app.core.database import get_db

            # Get database session
            async for db in get_db():
                await audit_service.log_event(
                    db=db,
                    action=AuditAction.RATE_LIMIT_EXCEEDED,
                    user_id=getattr(request.state.user, "id", None) if hasattr(request.state, "user") else None,
                    user_email=getattr(request.state.user, "email", None) if hasattr(request.state, "user") else None,
                    user_role=getattr(request.state.user, "role", None) if hasattr(request.state, "user") else None,
                    description=f"Rate limit exceeded on {request.url.path}",
                    target_type="endpoint",
                    target_id=request.url.path,
                    details={
                        "identifier": identifier,
                        "method": request.method,
                        "user_agent": request.headers.get("User-Agent")
                    },
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("User-Agent"),
                    request_method=request.method,
                    request_path=str(request.url.path),
                    severity=AuditSeverity.WARNING
                )
                break

        except Exception as e:
            logger.error(f"❌ Error logging rate limit violation: {e}")


import time


# Export rate limit decorator for easy use in routes
def rate_limit(limit_string: str):
    """
    Decorator for applying rate limits to specific endpoints

    Usage:
        @router.post("/login")
        @rate_limit("10/minute")
        async def login(...)

    Args:
        limit_string: Rate limit (e.g., "10/minute", "100/hour")
    """
    return limiter.limit(limit_string)


# Shorthand decorators for common limits
strict_rate_limit = limiter.limit("10/minute")
moderate_rate_limit = limiter.limit("60/minute")
relaxed_rate_limit = limiter.limit("200/minute")
