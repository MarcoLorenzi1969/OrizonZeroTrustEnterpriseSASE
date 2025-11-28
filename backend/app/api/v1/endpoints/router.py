"""
Orizon Zero Trust Connect - API v1 Router
For: Marco @ Syneto/Orizon
"""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    nodes,
    tunnels,
    acl,
    audit,
    twofa,
    metrics,
    provision,
    groups,
    user_management,
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(nodes.router, prefix="/nodes", tags=["Nodes"])
api_router.include_router(groups.router, prefix="/groups", tags=["Groups"])
api_router.include_router(tunnels.router, prefix="/tunnels", tags=["Tunnels"])
api_router.include_router(acl.router, prefix="/acl", tags=["Access Control"])
api_router.include_router(audit.router, prefix="/audit", tags=["Audit Logs"])
api_router.include_router(twofa.router, prefix="/2fa", tags=["Two-Factor Authentication"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["Metrics"])

# Public endpoints (no auth required)
api_router.include_router(provision.router, prefix="/provision", tags=["Provisioning"])

# User management
api_router.include_router(user_management.router, tags=["User Management"])
