"""
Orizon Zero Trust Connect - Auth Module
For: Marco @ Syneto/Orizon
"""

from app.auth.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    check_permission,
)
from app.auth.dependencies import (
    get_current_user,
    get_current_active_user,
    require_superuser,
    require_super_admin,
    require_admin,
    require_user,
    can_create_users,
    can_manage_nodes,
    can_manage_tunnels,
    can_view_logs,
)

__all__ = [
    "verify_password",
    "get_password_hash",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "check_permission",
    "get_current_user",
    "get_current_active_user",
    "require_superuser",
    "require_super_admin",
    "require_admin",
    "require_user",
    "can_create_users",
    "can_manage_nodes",
    "can_manage_tunnels",
    "can_view_logs",
]
