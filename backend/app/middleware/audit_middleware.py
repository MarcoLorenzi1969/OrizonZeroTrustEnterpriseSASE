"""
Audit Middleware for Orizon Zero Trust Connect
Automatically logs user actions to the audit system
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
from datetime import datetime
import uuid


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically log user actions"""

    async def dispatch(self, request: Request, call_next: Callable):
        # Process request
        response = await call_next(request)

        # Only log successful POST/PUT/DELETE requests (modifications)
        if request.method in ["POST", "PUT", "DELETE"] and 200 <= response.status_code < 300:
            # Get user from request state if available
            user = getattr(request.state, "user", None)
            
            if user:
                # Map paths to actions
                action = self._get_action_from_request(request)
                
                if action:
                    # Import here to avoid circular imports
                    from app.models.user_permissions import AccessLog, ServiceType
                    from app.core.database import SessionLocal
                    
                    try:
                        async with SessionLocal() as db:
                            log_entry = AccessLog(
                                id=str(uuid.uuid4()),
                                user_id=user.id,
                                node_id=None,  # Will be populated for node-specific actions
                                service_type=ServiceType.HTTP,
                                action=action,
                                source_ip=request.client.host if request.client else "unknown",
                                user_agent=request.headers.get("user-agent"),
                                success=True,
                                timestamp=datetime.utcnow()
                            )
                            
                            db.add(log_entry)
                            await db.commit()
                    except Exception as e:
                        print(f"Audit log error: {e}")
                        # Don't fail the request if logging fails

        return response

    def _get_action_from_request(self, request: Request) -> str:
        """Map request path and method to action name"""
        path = request.url.path
        method = request.method

        # User management actions
        if "/user-management/users" in path:
            if method == "POST":
                return "create_user"
            elif method == "PUT":
                return "update_user"
            elif method == "DELETE":
                return "delete_user"
        
        # Permission actions
        if "/permissions/grant" in path and method == "POST":
            return "grant_permission"
        if "/permissions/revoke" in path and method == "DELETE":
            return "revoke_permission"
        
        # Login/Logout
        if "/sso/login" in path and method == "POST":
            return "login"
        if "/sso/logout" in path and method == "POST":
            return "logout"
        
        # Node actions
        if "/nodes" in path:
            if method == "POST":
                return "create_node"
            elif method == "PUT":
                return "update_node"
            elif method == "DELETE":
                return "delete_node"
        
        return None
