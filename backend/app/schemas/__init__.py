"""
Orizon Zero Trust Connect - Schemas
For: Marco @ Syneto/Orizon
"""

from app.schemas.user import (
    TokenPayload,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserList,
    Token,
    LoginRequest,
    RefreshTokenRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    ChangePasswordRequest,
)
from app.schemas.node import (
    NodeCreate,
    NodeUpdate,
    NodeResponse,
    NodeList,
    NodeMetrics,
)
from app.schemas.tunnel import (
    TunnelCreate,
    TunnelUpdate,
    TunnelResponse,
    TunnelList,
)
from app.schemas.access_rule import (
    AccessRuleCreate,
    AccessRuleUpdate,
    AccessRuleResponse,
    AccessRuleList,
)

__all__ = [
    "TokenPayload",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserList",
    "Token",
    "LoginRequest",
    "RefreshTokenRequest",
    "PasswordResetRequest",
    "PasswordResetConfirm",
    "ChangePasswordRequest",
    "NodeCreate",
    "NodeUpdate",
    "NodeResponse",
    "NodeList",
    "NodeMetrics",
    "TunnelCreate",
    "TunnelUpdate",
    "TunnelResponse",
    "TunnelList",
    "AccessRuleCreate",
    "AccessRuleUpdate",
    "AccessRuleResponse",
    "AccessRuleList",
]
