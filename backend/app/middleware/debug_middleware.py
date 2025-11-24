"""
Debug Middleware for Orizon Zero Trust Connect
Intercepts all HTTP requests and logs them to the debug system
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import time
from datetime import datetime


class DebugMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests to debug system"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip debug endpoints to avoid infinite loop
        if request.url.path.startswith("/api/v1/debug"):
            return await call_next(request)

        # Import debug globals from debug endpoint
        try:
            from app.api.v1.endpoints.debug import debug_config, debug_events
        except ImportError:
            # Debug system not available
            return await call_next(request)

        # Check if debug is enabled
        if not debug_config.enabled:
            return await call_next(request)

        # Capture request info
        start_time = time.time()
        request_id = f"{int(start_time * 1000)}"

        # Get user info from request state if available
        user_email = None
        user_id = None
        if hasattr(request.state, "user"):
            user = request.state.user
            user_email = getattr(user, "email", None)
            user_id = getattr(user, "id", None)

        # Log request (without reading body to avoid conflicts)
        debug_events.append({
            "event_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "http_request",
            "severity": "info",
            "source": "middleware",
            "message": f"{request.method} {request.url.path}",
            "user_id": user_id,
            "user_email": user_email,
            "details": {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "headers": {k: v for k, v in request.headers.items() if k.lower() not in ["authorization", "cookie"]},
                "client_ip": request.client.host if request.client else None,
                "user_email": user_email,
                "user_id": user_id,
            }
        })

        # Process request
        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # Log response
            debug_events.append({
                "event_id": f"{request_id}_response",
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": "http_response",
                "severity": "info" if response.status_code < 400 else "warning" if response.status_code < 500 else "error",
                "source": "middleware",
                "message": f"{request.method} {request.url.path} → {response.status_code}",
                "user_id": user_id,
                "user_email": user_email,
                "details": {
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                }
            })

            return response

        except Exception as e:
            duration = time.time() - start_time

            # Log error
            debug_events.append({
                "event_id": f"{request_id}_error",
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": "http_error",
                "severity": "error",
                "source": "middleware",
                "message": f"{request.method} {request.url.path} → ERROR: {str(e)}",
                "user_id": user_id,
                "user_email": user_email,
                "details": {
                    "request_id": request_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration_ms": round(duration * 1000, 2),
                }
            })

            raise
