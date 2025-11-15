"""
Orizon Zero Trust Connect - Access Rule Models
For: Marco @ Syneto/Orizon
Zero Trust access control rules
"""

from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base


class RuleAction(str, enum.Enum):
    """Action to take when rule matches"""
    ALLOW = "allow"
    DENY = "deny"


class RuleProtocol(str, enum.Enum):
    """Network protocol"""
    TCP = "tcp"
    UDP = "udp"
    ICMP = "icmp"
    ALL = "all"


class AccessRule(Base):
    """Zero Trust access control rule"""
    
    __tablename__ = "access_rules"
    
    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    
    # Rule configuration
    action = Column(Enum(RuleAction), default=RuleAction.DENY, nullable=False)
    protocol = Column(Enum(RuleProtocol), default=RuleProtocol.ALL, nullable=False)
    priority = Column(Integer, default=100, nullable=False)  # Lower = higher priority
    
    # Source configuration
    source_node_id = Column(String(36), ForeignKey("nodes.id"), nullable=True)
    source_ip = Column(String(50), nullable=True)  # CIDR notation
    source_port = Column(Integer, nullable=True)
    
    # Destination configuration
    destination_node_id = Column(String(36), ForeignKey("nodes.id"), nullable=True)
    destination_ip = Column(String(50), nullable=True)  # CIDR notation
    destination_port = Column(Integer, nullable=True)
    
    # Time-based access control
    valid_from = Column(DateTime, nullable=True)
    valid_until = Column(DateTime, nullable=True)
    
    # Days of week (0=Monday, 6=Sunday)
    allowed_days = Column(JSON, default=list)  # [0,1,2,3,4] for Mon-Fri
    
    # Time of day (HH:MM format)
    allowed_time_start = Column(String(5), nullable=True)  # "09:00"
    allowed_time_end = Column(String(5), nullable=True)  # "17:00"
    
    # Status
    is_enabled = Column(Boolean, default=True)
    
    # Statistics
    match_count = Column(Integer, default=0)
    last_matched_at = Column(DateTime, nullable=True)
    
    # Metadata
    tags = Column(JSON, default=list)
    metadata = Column(JSON, default=dict)
    
    # Ownership
    node_id = Column(String(36), ForeignKey("nodes.id"), nullable=False)
    node = relationship("Node", back_populates="rules")
    
    created_by_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<AccessRule {self.name} ({self.action}) - Priority {self.priority}>"
    
    @property
    def is_valid(self) -> bool:
        """Check if rule is currently valid based on time constraints"""
        if not self.is_enabled:
            return False
        
        now = datetime.utcnow()
        
        # Check valid date range
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        
        # Check day of week
        if self.allowed_days and now.weekday() not in self.allowed_days:
            return False
        
        # Check time of day
        if self.allowed_time_start and self.allowed_time_end:
            current_time = now.strftime("%H:%M")
            if not (self.allowed_time_start <= current_time <= self.allowed_time_end):
                return False
        
        return True
