"""
Orizon Zero Trust Connect - ACL Rules API Endpoints
For: Marco @ Syneto/Orizon
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from loguru import logger

from app.core.database import get_db
from app.auth.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.services.acl_service import acl_service
from app.schemas.access_rule import AccessRuleCreate, AccessRuleResponse
from app.middleware.rate_limit import rate_limit

router = APIRouter()


@router.post("/", response_model=AccessRuleResponse, status_code=status.HTTP_201_CREATED)
@rate_limit("30/minute")
async def create_acl_rule(
    request: Request,
    rule_data: AccessRuleCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    Create new ACL rule

    Requires: Admin role or higher
    """
    try:
        rule = await acl_service.create_rule(
            db=db,
            source_node=rule_data.source_node_id,
            dest_node=rule_data.dest_node_id,
            protocol=rule_data.protocol,
            port=rule_data.port,
            action=rule_data.action,
            priority=rule_data.priority,
            created_by=str(current_user.id),
            description=rule_data.description
        )

        if not rule:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create ACL rule"
            )

        logger.info(f"✅ ACL rule created via API: {rule.id} by {current_user.email}")

        return AccessRuleResponse(
            id=str(rule.id),
            source_node_id=rule.source_node_id,
            dest_node_id=rule.dest_node_id,
            protocol=rule.protocol.value if rule.protocol else "any",
            port=rule.port or 0,
            action=rule.action.value,
            priority=rule.priority,
            description=rule.description,
            is_active=rule.is_active,
            created_at=rule.created_at,
            created_by=rule.created_by
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating ACL rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/", response_model=List[AccessRuleResponse])
async def get_all_acl_rules(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(require_role(UserRole.USER)),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all ACL rules with pagination

    Requires: Any authenticated user
    """
    try:
        rules = await acl_service.get_all_rules(db, skip=skip, limit=limit)

        return [
            AccessRuleResponse(
                id=str(rule.id),
                source_node_id=rule.source_node_id,
                dest_node_id=rule.dest_node_id,
                protocol=rule.protocol.value if rule.protocol else "any",
                port=rule.port or 0,
                action=rule.action.value,
                priority=rule.priority,
                description=rule.description,
                is_active=rule.is_active,
                created_at=rule.created_at,
                created_by=rule.created_by
            )
            for rule in rules
        ]

    except Exception as e:
        logger.error(f"❌ Error getting ACL rules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/node/{node_id}", response_model=List[AccessRuleResponse])
async def get_node_acl_rules(
    node_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all ACL rules for a specific node

    Requires: Any authenticated user
    """
    try:
        rules = await acl_service.get_rules_for_node(db, node_id)

        return [
            AccessRuleResponse(
                id=str(rule.id),
                source_node_id=rule.source_node_id,
                dest_node_id=rule.dest_node_id,
                protocol=rule.protocol.value if rule.protocol else "any",
                port=rule.port or 0,
                action=rule.action.value,
                priority=rule.priority,
                description=rule.description,
                is_active=rule.is_active,
                created_at=rule.created_at,
                created_by=rule.created_by
            )
            for rule in rules
        ]

    except Exception as e:
        logger.error(f"❌ Error getting node ACL rules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
@rate_limit("10/minute")
async def delete_acl_rule(
    request: Request,
    rule_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete ACL rule

    Requires: Admin role or higher
    """
    try:
        success = await acl_service.delete_rule(db, rule_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ACL rule {rule_id} not found"
            )

        logger.info(f"✅ ACL rule deleted via API: {rule_id} by {current_user.email}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting ACL rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{rule_id}/enable", status_code=status.HTTP_200_OK)
@rate_limit("20/minute")
async def enable_acl_rule(
    request: Request,
    rule_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    Enable ACL rule

    Requires: Admin role or higher
    """
    try:
        success = await acl_service.enable_rule(db, rule_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ACL rule {rule_id} not found"
            )

        logger.info(f"✅ ACL rule enabled via API: {rule_id} by {current_user.email}")

        return {"message": "ACL rule enabled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error enabling ACL rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{rule_id}/disable", status_code=status.HTTP_200_OK)
@rate_limit("20/minute")
async def disable_acl_rule(
    request: Request,
    rule_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    Disable ACL rule

    Requires: Admin role or higher
    """
    try:
        success = await acl_service.disable_rule(db, rule_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ACL rule {rule_id} not found"
            )

        logger.info(f"✅ ACL rule disabled via API: {rule_id} by {current_user.email}")

        return {"message": "ACL rule disabled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error disabling ACL rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
