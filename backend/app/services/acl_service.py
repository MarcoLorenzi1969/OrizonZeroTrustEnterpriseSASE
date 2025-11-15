"""
Orizon Zero Trust Connect - ACL Service
For: Marco @ Syneto/Orizon

Access Control List management for Zero Trust mesh network
Default policy: DENY ALL
"""

import uuid
from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, or_
from loguru import logger

from app.models.access_rule import AccessRule, RuleAction, RuleProtocol
from app.schemas.access_rule import ACLRuleCreate, ACLRuleResponse
from app.websocket.manager import ws_manager
from app.core.mongodb import get_mongodb


class ACLService:
    """
    Zero Trust Access Control List Service
    
    Features:
    - Rule-based access control (RBAC)
    - Default DENY ALL policy
    - Priority-based rule matching (1-100, 1 = highest)
    - Real-time rule propagation via WebSocket
    - Audit logging to MongoDB
    """
    
    # Priority levels
    PRIORITY_CRITICAL = 1  # Emergency/system rules
    PRIORITY_HIGH = 25     # Important business rules
    PRIORITY_MEDIUM = 50   # Standard rules
    PRIORITY_LOW = 75      # Optional/test rules
    PRIORITY_DEFAULT = 100 # Catch-all rules
    
    async def create_rule(
        self,
        db: AsyncSession,
        source_node: str,
        dest_node: str,
        protocol: str,
        port: int,
        action: str,
        priority: int,
        created_by: str,
        description: Optional[str] = None
    ) -> Optional[AccessRule]:
        """
        Create new ACL rule
        
        Args:
            db: Database session
            source_node: Source node ID or "*" for any
            dest_node: Destination node ID or "*" for any
            protocol: "tcp", "udp", "ssh", "https", or "any"
            port: Port number or 0 for any
            action: "allow" or "deny"
            priority: 1-100 (1 = highest priority)
            created_by: User ID who created the rule
            description: Optional rule description
            
        Returns:
            Created AccessRule or None on failure
        """
        try:
            # Validate inputs
            if priority < 1 or priority > 100:
                logger.error(f"❌ Invalid priority {priority}, must be 1-100")
                return None
            
            if action not in ["allow", "deny"]:
                logger.error(f"❌ Invalid action {action}")
                return None
            
            # Check for conflicting rules with same priority
            conflict = await self._check_rule_conflict(
                db, source_node, dest_node, protocol, port, priority
            )
            
            if conflict:
                logger.warning(
                    f"⚠️ Rule conflict detected at priority {priority}, "
                    "rule will be added but may not behave as expected"
                )
            
            # Create rule
            rule_id = str(uuid.uuid4())
            rule = AccessRule(
                id=rule_id,
                source_node_id=source_node,
                dest_node_id=dest_node,
                protocol=RuleProtocol(protocol.upper()) if protocol != "any" else None,
                port=port if port > 0 else None,
                action=RuleAction(action.upper()),
                priority=priority,
                description=description,
                created_by=created_by,
                created_at=datetime.utcnow(),
                is_active=True
            )
            
            db.add(rule)
            await db.commit()
            await db.refresh(rule)
            
            logger.info(
                f"✅ ACL rule created: {rule_id} "
                f"({source_node} → {dest_node}, {protocol}:{port}, {action}, priority {priority})"
            )
            
            # Apply rule to affected nodes
            await self.apply_rules_to_node(db, source_node)
            await self.apply_rules_to_node(db, dest_node)
            
            # Log to MongoDB for audit
            await self._log_acl_event("rule_created", {
                "rule_id": rule_id,
                "source_node": source_node,
                "dest_node": dest_node,
                "protocol": protocol,
                "port": port,
                "action": action,
                "priority": priority,
                "created_by": created_by
            })
            
            return rule
            
        except Exception as e:
            logger.error(f"❌ Failed to create ACL rule: {e}")
            await db.rollback()
            return None
    
    async def delete_rule(
        self,
        db: AsyncSession,
        rule_id: str
    ) -> bool:
        """Delete ACL rule"""
        try:
            # Get rule first to know affected nodes
            stmt = select(AccessRule).where(AccessRule.id == rule_id)
            result = await db.execute(stmt)
            rule = result.scalar_one_or_none()
            
            if not rule:
                logger.warning(f"⚠️ Rule {rule_id} not found")
                return False
            
            source_node = rule.source_node_id
            dest_node = rule.dest_node_id
            
            # Delete rule
            stmt = delete(AccessRule).where(AccessRule.id == rule_id)
            await db.execute(stmt)
            await db.commit()
            
            logger.info(f"❌ ACL rule deleted: {rule_id}")
            
            # Re-apply rules to affected nodes
            await self.apply_rules_to_node(db, source_node)
            await self.apply_rules_to_node(db, dest_node)
            
            # Log to MongoDB
            await self._log_acl_event("rule_deleted", {
                "rule_id": rule_id,
                "source_node": source_node,
                "dest_node": dest_node
            })
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete ACL rule {rule_id}: {e}")
            await db.rollback()
            return False
    
    async def get_rules_for_node(
        self,
        db: AsyncSession,
        node_id: str
    ) -> List[AccessRule]:
        """
        Get all ACL rules affecting a specific node
        Includes rules where node is source or destination
        """
        try:
            stmt = select(AccessRule).where(
                and_(
                    or_(
                        AccessRule.source_node_id == node_id,
                        AccessRule.dest_node_id == node_id,
                        AccessRule.source_node_id == "*",
                        AccessRule.dest_node_id == "*"
                    ),
                    AccessRule.is_active == True
                )
            ).order_by(AccessRule.priority.asc())
            
            result = await db.execute(stmt)
            rules = result.scalars().all()
            
            logger.debug(f"📋 Found {len(rules)} ACL rules for node {node_id}")
            
            return rules
            
        except Exception as e:
            logger.error(f"❌ Failed to get rules for node {node_id}: {e}")
            return []
    
    async def apply_rules_to_node(
        self,
        db: AsyncSession,
        node_id: str
    ) -> bool:
        """
        Apply all relevant ACL rules to a node via WebSocket
        
        The agent will receive rules and apply them locally using:
        - Linux: iptables
        - macOS: pf (Packet Filter)
        - Windows: netsh advfirewall
        
        Args:
            db: Database session
            node_id: Node to apply rules to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if node_id == "*":
                logger.debug("⚠️ Skipping rule application to wildcard node")
                return True
            
            # Get all rules for this node
            rules = await self.get_rules_for_node(db, node_id)
            
            # Convert rules to agent-friendly format
            rule_config = self._format_rules_for_agent(rules, node_id)
            
            # Send rules to agent via WebSocket
            message = {
                "type": "acl_update",
                "node_id": node_id,
                "rules": rule_config,
                "timestamp": datetime.utcnow().isoformat(),
                "default_policy": "DENY"  # Zero Trust
            }
            
            await ws_manager.send_user_message(node_id, message)
            
            logger.info(f"✅ Applied {len(rules)} ACL rules to node {node_id}")
            
            # Log event
            await self._log_acl_event("rules_applied", {
                "node_id": node_id,
                "rule_count": len(rules)
            })
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to apply rules to node {node_id}: {e}")
            return False
    
    async def check_access(
        self,
        db: AsyncSession,
        source: str,
        dest: str,
        protocol: str,
        port: int
    ) -> bool:
        """
        Check if access is allowed based on ACL rules
        
        Uses priority-based matching:
        1. Get all relevant rules (sorted by priority)
        2. Find first matching rule
        3. Return action (allow/deny)
        4. If no match, default DENY (Zero Trust)
        
        Args:
            db: Database session
            source: Source node ID
            dest: Destination node ID
            protocol: Protocol (tcp/udp/ssh/https)
            port: Port number
            
        Returns:
            True if access allowed, False if denied
        """
        try:
            # Get all active rules sorted by priority
            stmt = select(AccessRule).where(
                AccessRule.is_active == True
            ).order_by(AccessRule.priority.asc())
            
            result = await db.execute(stmt)
            rules = result.scalars().all()
            
            # Find first matching rule
            for rule in rules:
                if self._rule_matches(rule, source, dest, protocol, port):
                    action_allowed = (rule.action == RuleAction.ALLOW)
                    
                    logger.debug(
                        f"🔍 ACL check: {source} → {dest}:{port}/{protocol} = "
                        f"{'✅ ALLOW' if action_allowed else '❌ DENY'} "
                        f"(rule {rule.id}, priority {rule.priority})"
                    )
                    
                    # Log access check
                    await self._log_acl_event("access_check", {
                        "source": source,
                        "dest": dest,
                        "protocol": protocol,
                        "port": port,
                        "result": "allow" if action_allowed else "deny",
                        "rule_id": rule.id,
                        "priority": rule.priority
                    })
                    
                    return action_allowed
            
            # No matching rule - default DENY (Zero Trust)
            logger.debug(
                f"🔍 ACL check: {source} → {dest}:{port}/{protocol} = "
                f"❌ DENY (default policy)"
            )
            
            await self._log_acl_event("access_check", {
                "source": source,
                "dest": dest,
                "protocol": protocol,
                "port": port,
                "result": "deny",
                "reason": "default_policy"
            })
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error in access check: {e}")
            # Fail secure - deny on error
            return False
    
    async def get_all_rules(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> List[AccessRule]:
        """Get all ACL rules with pagination"""
        try:
            stmt = select(AccessRule).where(
                AccessRule.is_active == True
            ).order_by(
                AccessRule.priority.asc()
            ).offset(skip).limit(limit)
            
            result = await db.execute(stmt)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"❌ Failed to get all rules: {e}")
            return []
    
    async def enable_rule(
        self,
        db: AsyncSession,
        rule_id: str
    ) -> bool:
        """Enable a disabled ACL rule"""
        try:
            stmt = select(AccessRule).where(AccessRule.id == rule_id)
            result = await db.execute(stmt)
            rule = result.scalar_one_or_none()
            
            if not rule:
                return False
            
            rule.is_active = True
            rule.updated_at = datetime.utcnow()
            await db.commit()
            
            # Re-apply rules to affected nodes
            await self.apply_rules_to_node(db, rule.source_node_id)
            await self.apply_rules_to_node(db, rule.dest_node_id)
            
            logger.info(f"✅ ACL rule enabled: {rule_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to enable rule {rule_id}: {e}")
            return False
    
    async def disable_rule(
        self,
        db: AsyncSession,
        rule_id: str
    ) -> bool:
        """Disable an ACL rule without deleting it"""
        try:
            stmt = select(AccessRule).where(AccessRule.id == rule_id)
            result = await db.execute(stmt)
            rule = result.scalar_one_or_none()
            
            if not rule:
                return False
            
            rule.is_active = False
            rule.updated_at = datetime.utcnow()
            await db.commit()
            
            # Re-apply rules to affected nodes
            await self.apply_rules_to_node(db, rule.source_node_id)
            await self.apply_rules_to_node(db, rule.dest_node_id)
            
            logger.info(f"⏸️ ACL rule disabled: {rule_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to disable rule {rule_id}: {e}")
            return False
    
    def _rule_matches(
        self,
        rule: AccessRule,
        source: str,
        dest: str,
        protocol: str,
        port: int
    ) -> bool:
        """Check if rule matches the access request"""
        # Check source
        if rule.source_node_id != "*" and rule.source_node_id != source:
            return False
        
        # Check destination
        if rule.dest_node_id != "*" and rule.dest_node_id != dest:
            return False
        
        # Check protocol
        if rule.protocol and rule.protocol.value.lower() != protocol.lower():
            return False
        
        # Check port
        if rule.port and rule.port != port:
            return False
        
        return True
    
    def _format_rules_for_agent(
        self,
        rules: List[AccessRule],
        node_id: str
    ) -> List[Dict]:
        """
        Format rules for agent consumption
        
        Agent receives rules in this format for local firewall application:
        {
            "source": "node-id or *",
            "dest": "node-id or *",
            "protocol": "tcp/udp/ssh/https/any",
            "port": 22 or 0 for any,
            "action": "allow/deny",
            "priority": 1-100
        }
        """
        formatted_rules = []
        
        for rule in rules:
            formatted_rules.append({
                "rule_id": rule.id,
                "source": rule.source_node_id,
                "dest": rule.dest_node_id,
                "protocol": rule.protocol.value.lower() if rule.protocol else "any",
                "port": rule.port if rule.port else 0,
                "action": rule.action.value.lower(),
                "priority": rule.priority,
                "description": rule.description
            })
        
        return formatted_rules
    
    async def _check_rule_conflict(
        self,
        db: AsyncSession,
        source: str,
        dest: str,
        protocol: str,
        port: int,
        priority: int
    ) -> bool:
        """Check if there's a conflicting rule at the same priority"""
        stmt = select(AccessRule).where(
            and_(
                AccessRule.source_node_id == source,
                AccessRule.dest_node_id == dest,
                AccessRule.priority == priority,
                AccessRule.is_active == True
            )
        )
        
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None
    
    async def _log_acl_event(self, event_type: str, details: Dict):
        """Log ACL event to MongoDB for audit"""
        try:
            mongodb = await get_mongodb()
            
            event = {
                "event_type": event_type,
                "details": details,
                "timestamp": datetime.utcnow()
            }
            
            await mongodb["acl_logs"].insert_one(event)
            
        except Exception as e:
            logger.error(f"❌ Error logging ACL event: {e}")


# Global ACL service instance
acl_service = ACLService()
