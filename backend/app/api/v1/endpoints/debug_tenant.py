"""
Orizon Zero Trust - Debug Endpoint for Groups-Tenants-Nodes
Endpoint di debug per visualizzare la catena completa delle associazioni
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import List, Dict, Any

from app.core.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/groups-tenants-nodes", response_model=Dict[str, Any])
async def debug_groups_tenants_nodes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Endpoint di debug per visualizzare la catena completa:
    Groups → Tenants → Nodes

    Mostra tutte le associazioni e relazioni nel sistema multi-tenant
    """

    result = {}

    # 1. Get all groups with their members and tenant associations
    query = text("""
        SELECT
            g.id as group_id,
            g.name as group_name,
            g.description as group_description,
            COUNT(DISTINCT ug.user_id) as member_count,
            COUNT(DISTINCT gt.tenant_id) as tenant_count,
            json_agg(DISTINCT jsonb_build_object(
                'user_id', u.id,
                'user_email', u.email,
                'role_in_group', ug.role_in_group
            )) FILTER (WHERE u.id IS NOT NULL) as members,
            json_agg(DISTINCT jsonb_build_object(
                'tenant_id', gt.tenant_id,
                'tenant_name', t.name,
                'permissions', gt.permissions
            )) FILTER (WHERE gt.tenant_id IS NOT NULL) as tenants
        FROM groups g
        LEFT JOIN user_groups ug ON g.id = ug.group_id
        LEFT JOIN users u ON ug.user_id = u.id
        LEFT JOIN group_tenants gt ON g.id = gt.group_id AND gt.is_active = true
        LEFT JOIN tenants t ON gt.tenant_id = t.id
        WHERE g.is_active = true
        GROUP BY g.id, g.name, g.description
        ORDER BY g.name
    """)

    groups_result = await db.execute(query)
    groups = []
    for row in groups_result:
        groups.append({
            "group_id": row.group_id,
            "group_name": row.group_name,
            "description": row.group_description,
            "member_count": row.member_count,
            "tenant_count": row.tenant_count,
            "members": row.members if row.members else [],
            "tenants": row.tenants if row.tenants else []
        })

    result["groups"] = groups

    # 2. Get all tenants with their groups and nodes
    query = text("""
        SELECT
            t.id as tenant_id,
            t.name as tenant_name,
            t.display_name,
            t.slug,
            t.company_info,
            t.settings,
            t.quota,
            COUNT(DISTINCT gt.group_id) as group_count,
            COUNT(DISTINCT tn.node_id) as node_count,
            json_agg(DISTINCT jsonb_build_object(
                'group_id', g.id,
                'group_name', g.name,
                'permissions', gt.permissions
            )) FILTER (WHERE g.id IS NOT NULL) as groups,
            json_agg(DISTINCT jsonb_build_object(
                'node_id', n.id,
                'node_name', n.name,
                'node_type', n.node_type,
                'status', n.status,
                'config', tn.node_config
            )) FILTER (WHERE n.id IS NOT NULL) as nodes
        FROM tenants t
        LEFT JOIN group_tenants gt ON t.id = gt.tenant_id AND gt.is_active = true
        LEFT JOIN groups g ON gt.group_id = g.id
        LEFT JOIN tenant_nodes tn ON t.id = tn.tenant_id AND tn.is_active = true
        LEFT JOIN nodes n ON tn.node_id = n.id
        WHERE t.is_active = true
        GROUP BY t.id, t.name, t.display_name, t.slug, t.company_info, t.settings, t.quota
        ORDER BY t.name
    """)

    tenants_result = await db.execute(query)
    tenants = []
    for row in tenants_result:
        tenants.append({
            "tenant_id": row.tenant_id,
            "tenant_name": row.tenant_name,
            "display_name": row.display_name,
            "slug": row.slug,
            "company_info": row.company_info,
            "settings": row.settings,
            "quota": row.quota,
            "group_count": row.group_count,
            "node_count": row.node_count,
            "groups": row.groups if row.groups else [],
            "nodes": row.nodes if row.nodes else []
        })

    result["tenants"] = tenants

    # 3. Get all nodes with their tenant associations
    query = text("""
        SELECT
            n.id as node_id,
            n.name as node_name,
            n.hostname,
            n.node_type,
            n.status,
            n.public_ip,
            n.private_ip,
            COUNT(DISTINCT tn.tenant_id) as tenant_count,
            json_agg(DISTINCT jsonb_build_object(
                'tenant_id', t.id,
                'tenant_name', t.name,
                'config', tn.node_config
            )) FILTER (WHERE t.id IS NOT NULL) as tenants
        FROM nodes n
        LEFT JOIN tenant_nodes tn ON n.id = tn.node_id AND tn.is_active = true
        LEFT JOIN tenants t ON tn.tenant_id = t.id
        GROUP BY n.id, n.name, n.hostname, n.node_type, n.status, n.public_ip, n.private_ip
        ORDER BY n.name
    """)

    nodes_result = await db.execute(query)
    nodes = []
    for row in nodes_result:
        nodes.append({
            "node_id": row.node_id,
            "node_name": row.node_name,
            "hostname": row.hostname,
            "node_type": row.node_type,
            "status": row.status,
            "public_ip": row.public_ip,
            "private_ip": row.private_ip,
            "tenant_count": row.tenant_count,
            "tenants": row.tenants if row.tenants else []
        })

    result["nodes"] = nodes

    # 4. Summary
    result["summary"] = {
        "total_groups": len(groups),
        "total_tenants": len(tenants),
        "total_nodes": len(nodes),
        "total_group_tenant_associations": sum(g["tenant_count"] for g in groups),
        "total_tenant_node_associations": sum(t["node_count"] for t in tenants),
        "current_user": {
            "id": current_user.id,
            "email": current_user.email,
            "role": current_user.role.value
        }
    }

    return result


@router.get("/tenant-hierarchy/{tenant_id}", response_model=Dict[str, Any])
async def debug_tenant_hierarchy(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mostra la gerarchia completa di un tenant specifico:
    Tenant → Groups → Users
    Tenant → Nodes
    """

    # Get tenant info
    query = text("""
        SELECT
            t.*,
            u.email as created_by_email
        FROM tenants t
        LEFT JOIN users u ON t.created_by_id = u.id
        WHERE t.id = :tenant_id
    """)

    tenant_result = await db.execute(query, {"tenant_id": tenant_id})
    tenant_row = tenant_result.first()

    if not tenant_row:
        return {"error": "Tenant not found"}

    tenant_info = {
        "id": tenant_row.id,
        "name": tenant_row.name,
        "display_name": tenant_row.display_name,
        "slug": tenant_row.slug,
        "company_info": tenant_row.company_info,
        "settings": tenant_row.settings,
        "quota": tenant_row.quota,
        "created_by": tenant_row.created_by_email,
        "created_at": str(tenant_row.created_at)
    }

    # Get groups with their users
    query = text("""
        SELECT
            g.id as group_id,
            g.name as group_name,
            gt.permissions,
            json_agg(jsonb_build_object(
                'user_id', u.id,
                'user_email', u.email,
                'user_role', u.role,
                'role_in_group', ug.role_in_group
            )) as users
        FROM group_tenants gt
        JOIN groups g ON gt.group_id = g.id
        LEFT JOIN user_groups ug ON g.id = ug.group_id
        LEFT JOIN users u ON ug.user_id = u.id
        WHERE gt.tenant_id = :tenant_id AND gt.is_active = true
        GROUP BY g.id, g.name, gt.permissions
    """)

    groups_result = await db.execute(query, {"tenant_id": tenant_id})
    groups = []
    for row in groups_result:
        groups.append({
            "group_id": row.group_id,
            "group_name": row.group_name,
            "permissions": row.permissions,
            "users": row.users if row.users else []
        })

    # Get nodes
    query = text("""
        SELECT
            n.id as node_id,
            n.name as node_name,
            n.hostname,
            n.node_type,
            n.status,
            n.public_ip,
            tn.node_config
        FROM tenant_nodes tn
        JOIN nodes n ON tn.node_id = n.id
        WHERE tn.tenant_id = :tenant_id AND tn.is_active = true
    """)

    nodes_result = await db.execute(query, {"tenant_id": tenant_id})
    nodes = []
    for row in nodes_result:
        nodes.append({
            "node_id": row.node_id,
            "node_name": row.node_name,
            "hostname": row.hostname,
            "node_type": row.node_type,
            "status": row.status,
            "public_ip": row.public_ip,
            "config": row.node_config
        })

    return {
        "tenant": tenant_info,
        "groups": groups,
        "nodes": nodes,
        "statistics": {
            "total_groups": len(groups),
            "total_nodes": len(nodes),
            "total_users": sum(len(g["users"]) for g in groups)
        }
    }
