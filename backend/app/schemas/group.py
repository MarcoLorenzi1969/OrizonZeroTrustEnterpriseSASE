"""
Orizon Zero Trust Connect - Group Schemas
For: Marco @ Syneto/Orizon
Pydantic schemas for groups
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.group import GroupRole


# ==================== GROUP SCHEMAS ====================

class GroupBase(BaseModel):
    """Base group schema"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class GroupCreate(GroupBase):
    """Schema for creating new group"""
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict)


class GroupUpdate(BaseModel):
    """Schema for updating group"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class GroupResponse(GroupBase):
    """Group schema for API responses"""
    id: str
    settings: Dict[str, Any]
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime]
    is_active: bool

    # Counts
    member_count: Optional[int] = 0
    node_count: Optional[int] = 0

    class Config:
        from_attributes = True


class GroupList(BaseModel):
    """Schema for list of groups"""
    groups: List[GroupResponse]
    total: int


# ==================== USER-GROUP SCHEMAS ====================

class UserGroupBase(BaseModel):
    """Base user-group association"""
    user_id: str
    group_id: str


class AddUserToGroup(BaseModel):
    """Schema for adding user to group"""
    user_id: str
    role_in_group: GroupRole = GroupRole.MEMBER
    permissions: Optional[Dict[str, Any]] = Field(default_factory=dict)


class AddUsersToGroup(BaseModel):
    """Schema for adding multiple users to group"""
    user_ids: List[str]
    role_in_group: GroupRole = GroupRole.MEMBER
    permissions: Optional[Dict[str, Any]] = Field(default_factory=dict)


class UpdateUserRoleInGroup(BaseModel):
    """Schema for updating user role in group"""
    role_in_group: GroupRole
    permissions: Optional[Dict[str, Any]] = None


class UserGroupResponse(BaseModel):
    """User-group association for API responses"""
    id: str
    user_id: str
    group_id: str
    role_in_group: GroupRole
    permissions: Dict[str, Any]
    added_at: datetime

    class Config:
        from_attributes = True


class GroupMemberResponse(BaseModel):
    """Group member with user details"""
    user_id: str
    email: str
    username: str
    full_name: Optional[str]
    role_in_group: GroupRole
    permissions: Dict[str, Any]
    added_at: datetime


class GroupMembersList(BaseModel):
    """Schema for list of group members"""
    members: List[GroupMemberResponse]
    total: int


# ==================== NODE-GROUP SCHEMAS ====================

class NodeGroupBase(BaseModel):
    """Base node-group association"""
    node_id: str
    group_id: str


class AddNodeToGroup(BaseModel):
    """Schema for adding node to group"""
    node_id: str
    permissions: Dict[str, bool] = Field(
        default_factory=lambda: {"ssh": True, "rdp": False, "vnc": False}
    )


class AddNodesToGroup(BaseModel):
    """Schema for adding multiple nodes to group"""
    node_ids: List[str]
    permissions: Dict[str, bool] = Field(
        default_factory=lambda: {"ssh": True, "rdp": False, "vnc": False}
    )


class UpdateNodePermissionsInGroup(BaseModel):
    """Schema for updating node permissions in group"""
    permissions: Dict[str, bool]


class NodeGroupResponse(BaseModel):
    """Node-group association for API responses"""
    id: str
    node_id: str
    group_id: str
    permissions: Dict[str, bool]
    added_at: datetime

    class Config:
        from_attributes = True


class GroupNodeResponse(BaseModel):
    """Group node with node details"""
    node_id: str
    name: str
    hostname: str
    status: str
    node_type: str
    permissions: Dict[str, bool]
    added_at: datetime


class GroupNodesList(BaseModel):
    """Schema for list of group nodes"""
    nodes: List[GroupNodeResponse]
    total: int


# ==================== ACCESS CHECK SCHEMAS ====================

class CheckAccessRequest(BaseModel):
    """Request to check user access to node"""
    node_id: str
    permission_type: str = "ssh"  # ssh, rdp, vnc


class CheckAccessResponse(BaseModel):
    """Response for access check"""
    has_access: bool
    reason: Optional[str] = None
