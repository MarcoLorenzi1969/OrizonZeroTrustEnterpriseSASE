"""
Orizon Zero Trust Connect - Group Models
For: Marco @ Syneto/Orizon
Group-Based Access Control (GBAC)
"""

from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from app.core.database import Base


class GroupRole(str, enum.Enum):
    """Role within a group"""
    OWNER = "owner"      # Full control, can delete group
    ADMIN = "admin"      # Can manage members and nodes
    MEMBER = "member"    # Can access nodes only


class Group(Base):
    """Group model for organizing users and nodes"""

    __tablename__ = "groups"

    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(500), nullable=True)

    # Settings JSONB: {allow_terminal, allow_rdp, allow_vnc, max_concurrent_sessions}
    settings = Column(JSON, default=dict, nullable=False)

    # Creator
    created_by = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    creator = relationship("User", foreign_keys=[created_by], backref="owned_groups")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Soft delete
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    user_associations = relationship("UserGroup", back_populates="group", cascade="all, delete-orphan")
    node_associations = relationship("NodeGroup", back_populates="group", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Group(id={self.id}, name={self.name})>"


class UserGroup(Base):
    """Many-to-many: Users <-> Groups"""

    __tablename__ = "user_groups"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    group_id = Column(String(36), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)

    # Role in this specific group
    role_in_group = Column(Enum(GroupRole), default=GroupRole.MEMBER, nullable=False, index=True)

    # Custom permissions override (JSONB): {allow_terminal, allow_rdp, ...}
    # If empty, inherit from group settings
    permissions = Column(JSON, default=dict, nullable=False)

    # Who added this user to the group
    added_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    adder = relationship("User", foreign_keys=[added_by])

    # Timestamp
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="group_memberships")
    group = relationship("Group", back_populates="user_associations")

    def __repr__(self):
        return f"<UserGroup(user_id={self.user_id}, group_id={self.group_id}, role={self.role_in_group})>"


class NodeGroup(Base):
    """Many-to-many: Nodes <-> Groups"""

    __tablename__ = "node_groups"

    id = Column(String(36), primary_key=True, index=True)
    node_id = Column(String(36), ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    group_id = Column(String(36), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)

    # Permissions for this node in this group (JSONB)
    # {ssh: true, rdp: false, vnc: false, sftp: true}
    permissions = Column(JSON, default={"ssh": True, "rdp": False, "vnc": False}, nullable=False)

    # Who added this node to the group
    added_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    adder = relationship("User", foreign_keys=[added_by])

    # Timestamp
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    node = relationship("Node", foreign_keys=[node_id], backref="group_memberships")
    group = relationship("Group", back_populates="node_associations")

    def __repr__(self):
        return f"<NodeGroup(node_id={self.node_id}, group_id={self.group_id})>"
