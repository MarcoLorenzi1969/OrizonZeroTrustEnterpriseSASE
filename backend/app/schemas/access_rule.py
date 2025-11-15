"""
Orizon Zero Trust Connect - Access Rule Schemas
For: Marco @ Syneto/Orizon
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.access_rule import RuleAction, RuleProtocol


class AccessRuleBase(BaseModel):
    """Base access rule schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    action: RuleAction
    protocol: RuleProtocol = RuleProtocol.ALL
    priority: int = Field(default=100, ge=1, le=1000)


class AccessRuleCreate(AccessRuleBase):
    """Schema for creating new access rule"""
    node_id: str
    source_ip: Optional[str] = None
    source_port: Optional[int] = Field(None, ge=1, le=65535)
    destination_ip: Optional[str] = None
    destination_port: Optional[int] = Field(None, ge=1, le=65535)
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None


class AccessRuleUpdate(BaseModel):
    """Schema for updating access rule"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    action: Optional[RuleAction] = None
    priority: Optional[int] = Field(None, ge=1, le=1000)
    is_enabled: Optional[bool] = None


class AccessRuleResponse(AccessRuleBase):
    """Access rule schema for API responses"""
    id: str
    node_id: str
    source_ip: Optional[str]
    source_port: Optional[int]
    destination_ip: Optional[str]
    destination_port: Optional[int]
    is_enabled: bool
    match_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class AccessRuleList(BaseModel):
    """Schema for list of access rules"""
    rules: List[AccessRuleResponse]
    total: int
