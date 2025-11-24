"""
Orizon Zero Trust - Advanced Debug System
Sistema di debug completo per tracciamento end-to-end
Integrato con MCP per analisi con Claude Code
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
import json
import io
import asyncio
from collections import deque

from app.core.database import get_db
from app.auth.dependencies import get_current_user, require_role
from app.models.user import User, UserRole

router = APIRouter(tags=["debug"])


class DebugEvent(BaseModel):
    """Evento di debug completo"""
    event_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    event_type: str  # "api_call", "db_query", "auth", "error", "frontend", "click", "navigation"
    severity: str  # "debug", "info", "warning", "error", "critical"
    source: str  # "backend", "frontend", "database", "redis"
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    session_id: Optional[str] = None

    # Request info
    method: Optional[str] = None
    url: Optional[str] = None
    path: Optional[str] = None
    status_code: Optional[int] = None

    # Timing
    duration_ms: Optional[float] = None

    # Context
    message: str
    details: Dict[str, Any] = {}

    # Stack trace for errors
    stack_trace: Optional[str] = None

    # Browser info
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None


class DebugConfig(BaseModel):
    """Configurazione debug"""
    enabled: bool
    log_frontend: bool = True
    log_backend: bool = True
    log_database: bool = True
    log_auth: bool = True
    log_errors_only: bool = False
    max_events: int = 10000
    retention_hours: int = 24


class DebugExport(BaseModel):
    """Export dei log per analisi"""
    export_id: str
    generated_at: datetime
    total_events: int
    time_range: Dict[str, datetime]
    events: List[DebugEvent]
    summary: Dict[str, Any]


# In-memory storage per debug events (in produzione usare Redis o DB)
debug_events: deque = deque(maxlen=10000)
debug_config = DebugConfig(enabled=False)  # Disabilitato di default
event_counter = 0


def get_event_timestamp(event: dict) -> datetime:
    """Helper to safely extract timestamp from event (returns naive UTC datetime)"""
    ts = event.get("timestamp")
    if isinstance(ts, datetime):
        # Remove timezone info if present to make naive
        return ts.replace(tzinfo=None) if ts.tzinfo else ts
    elif isinstance(ts, str):
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        # Remove timezone to make naive
        return dt.replace(tzinfo=None) if dt.tzinfo else dt
    else:
        return datetime(2000, 1, 1)  # Fallback


def generate_event_id() -> str:
    """Genera ID univoco per evento"""
    global event_counter
    event_counter += 1
    return f"evt_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{event_counter}"


@router.get("/status")
async def get_debug_status(
    current_user: User = Depends(require_role(UserRole.SUPERUSER))
):
    """Ottieni stato del sistema di debug"""
    return {
        "debug_enabled": debug_config.enabled,
        "config": debug_config.dict(),
        "total_events": len(debug_events),
        "memory_usage_mb": len(str(debug_events)) / 1024 / 1024,
        "oldest_event": debug_events[0]["timestamp"] if debug_events else None,
        "newest_event": debug_events[-1]["timestamp"] if debug_events else None
    }


@router.post("/enable")
async def enable_debug(
    config: Optional[DebugConfig] = None,
    current_user: User = Depends(require_role(UserRole.SUPERUSER))
):
    """Abilita sistema di debug"""
    global debug_config

    if config:
        debug_config = config
    else:
        debug_config.enabled = True

    # Log evento di attivazione
    log_debug_event(
        event_type="system",
        severity="info",
        source="backend",
        message=f"Debug system enabled by {current_user.email}",
        user_id=current_user.id,
        user_email=current_user.email,
        details=debug_config.dict()
    )

    return {
        "status": "enabled",
        "config": debug_config.dict(),
        "message": "Debug system is now active. All events will be tracked."
    }


@router.post("/disable")
async def disable_debug(
    current_user: User = Depends(require_role(UserRole.SUPERUSER))
):
    """Disabilita sistema di debug"""
    global debug_config

    debug_config.enabled = False

    return {
        "status": "disabled",
        "events_captured": len(debug_events),
        "message": "Debug system disabled. Events preserved in memory."
    }


@router.post("/clear")
async def clear_debug_events(
    current_user: User = Depends(require_role(UserRole.SUPERUSER))
):
    """Cancella tutti gli eventi di debug"""
    count = len(debug_events)
    debug_events.clear()

    return {
        "status": "cleared",
        "events_deleted": count,
        "message": f"Deleted {count} debug events"
    }


@router.post("/event")
async def log_debug_event_api(
    event: DebugEvent,
    current_user: User = Depends(get_current_user)
):
    """API per loggare evento di debug (da frontend o altri sistemi)"""
    if not debug_config.enabled:
        return {"status": "ignored", "reason": "debug_disabled"}

    # Aggiungi info utente se non presente
    if not event.user_id:
        event.user_id = current_user.id
        event.user_email = current_user.email

    # Genera ID se non presente
    if not hasattr(event, 'event_id') or not event.event_id:
        event.event_id = generate_event_id()

    # Genera timestamp se non presente
    if not hasattr(event, 'timestamp') or not event.timestamp:
        event.timestamp = datetime.utcnow()

    # Aggiungi a storage
    debug_events.append(event.dict())

    return {
        "status": "logged",
        "event_id": event.event_id
    }


def log_debug_event(
    event_type: str,
    severity: str,
    source: str,
    message: str,
    user_id: Optional[str] = None,
    user_email: Optional[str] = None,
    **kwargs
):
    """Helper function per loggare eventi da backend"""
    if not debug_config.enabled:
        return

    event = {
        "event_id": generate_event_id(),
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "severity": severity,
        "source": source,
        "message": message,
        "user_id": user_id,
        "user_email": user_email,
        **kwargs
    }

    debug_events.append(event)


@router.get("/events")
async def get_debug_events(
    limit: int = 100,
    offset: int = 0,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    source: Optional[str] = None,
    user_id: Optional[str] = None,
    current_user: User = Depends(require_role(UserRole.SUPERUSER))
):
    """Recupera eventi di debug con filtri"""
    events = list(debug_events)

    # Applica filtri
    if event_type:
        events = [e for e in events if e.get("event_type") == event_type]
    if severity:
        events = [e for e in events if e.get("severity") == severity]
    if source:
        events = [e for e in events if e.get("source") == source]
    if user_id:
        events = [e for e in events if e.get("user_id") == user_id]

    # Ordina per timestamp (più recenti prima)
    # Handle None timestamps by using a default datetime for sorting
    from datetime import datetime
    def get_sort_key(event):
        ts = event.get("timestamp")
        if ts is None:
            return datetime.min
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts.replace('Z', '+00:00'))
            except:
                return datetime.min
        return ts

    events = sorted(events, key=get_sort_key, reverse=True)

    # Paginazione
    total = len(events)
    events = events[offset:offset + limit]

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "events": events
    }


@router.get("/export")
async def export_debug_logs(
    format: str = "json",  # "json" or "txt"
    time_range_hours: int = 24,
    current_user: User = Depends(require_role(UserRole.SUPERUSER))
):
    """
    Esporta tutti i log di debug per analisi con Claude Code

    Formati disponibili:
    - json: Export strutturato per elaborazione programmatica
    - txt: Export leggibile per analisi manuale
    """
    events = list(debug_events)

    # Filtra per time range
    cutoff_time = datetime.utcnow() - timedelta(hours=time_range_hours)
    events = [
        e for e in events
        if get_event_timestamp(e) > cutoff_time
    ]

    # Genera summary
    summary = {
        "total_events": len(events),
        "by_type": {},
        "by_severity": {},
        "by_source": {},
        "errors_count": len([e for e in events if e.get("severity") in ["error", "critical"]]),
        "time_range": {
            "start": events[-1]["timestamp"] if events else None,
            "end": events[0]["timestamp"] if events else None
        }
    }

    # Conta per tipo
    for event in events:
        event_type = event.get("event_type", "unknown")
        severity = event.get("severity", "unknown")
        source = event.get("source", "unknown")

        summary["by_type"][event_type] = summary["by_type"].get(event_type, 0) + 1
        summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
        summary["by_source"][source] = summary["by_source"].get(source, 0) + 1

    if format == "json":
        # Export JSON strutturato
        export_data = {
            "export_id": generate_event_id(),
            "generated_at": datetime.utcnow().isoformat(),
            "generated_by": current_user.email,
            "total_events": len(events),
            "time_range": summary["time_range"],
            "summary": summary,
            "events": events
        }

        # Crea file JSON
        json_str = json.dumps(export_data, indent=2, default=str)

        return StreamingResponse(
            io.BytesIO(json_str.encode()),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=orizon_debug_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            }
        )

    else:  # txt format
        # Export testuale leggibile
        lines = []
        lines.append("=" * 80)
        lines.append("ORIZON ZERO TRUST - DEBUG LOG EXPORT")
        lines.append("=" * 80)
        lines.append(f"Generated: {datetime.utcnow().isoformat()}")
        lines.append(f"Generated by: {current_user.email}")
        lines.append(f"Total events: {len(events)}")
        lines.append(f"Time range: {time_range_hours} hours")
        lines.append("=" * 80)
        lines.append("")

        # Summary
        lines.append("SUMMARY")
        lines.append("-" * 80)
        lines.append(f"Events by type:")
        for k, v in summary["by_type"].items():
            lines.append(f"  {k}: {v}")
        lines.append(f"\nEvents by severity:")
        for k, v in summary["by_severity"].items():
            lines.append(f"  {k}: {v}")
        lines.append(f"\nEvents by source:")
        for k, v in summary["by_source"].items():
            lines.append(f"  {k}: {v}")
        lines.append("")
        lines.append("=" * 80)
        lines.append("EVENTS")
        lines.append("=" * 80)
        lines.append("")

        # Eventi
        for event in events:
            lines.append(f"[{event.get('timestamp')}] {event.get('severity', '').upper()} - {event.get('event_type')}")
            lines.append(f"  Source: {event.get('source')}")
            if event.get('user_email'):
                lines.append(f"  User: {event.get('user_email')}")
            lines.append(f"  Message: {event.get('message')}")
            if event.get('method') and event.get('path'):
                lines.append(f"  Request: {event.get('method')} {event.get('path')}")
            if event.get('status_code'):
                lines.append(f"  Status: {event.get('status_code')}")
            if event.get('duration_ms'):
                lines.append(f"  Duration: {event.get('duration_ms')}ms")
            if event.get('details'):
                lines.append(f"  Details: {json.dumps(event.get('details'), indent=4)}")
            if event.get('stack_trace'):
                lines.append(f"  Stack trace:\n{event.get('stack_trace')}")
            lines.append("")

        txt_content = "\n".join(lines)

        return StreamingResponse(
            io.BytesIO(txt_content.encode()),
            media_type="text/plain",
            headers={
                "Content-Disposition": f"attachment; filename=orizon_debug_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt"
            }
        )


@router.get("/mcp-export")
async def mcp_export(
    current_user: User = Depends(require_role(UserRole.SUPERUSER))
):
    """
    Export ottimizzato per analisi con Claude Code via MCP

    Formato strutturato per permettere a Claude di:
    - Analizzare il flow completo dell'applicazione
    - Identificare errori e bottleneck
    - Suggerire ottimizzazioni
    - Debug end-to-end
    """
    events = list(debug_events)

    # Organizza eventi per session
    sessions = {}
    for event in events:
        session_id = event.get("session_id", "no_session")
        if session_id not in sessions:
            sessions[session_id] = []
        sessions[session_id].append(event)

    # Analisi automatica
    analysis = {
        "errors": [e for e in events if e.get("severity") in ["error", "critical"]],
        "slow_requests": [e for e in events if e.get("duration_ms", 0) > 1000],
        "auth_events": [e for e in events if e.get("event_type") == "auth"],
        "api_calls": [e for e in events if e.get("event_type") == "api_call"],
        "frontend_errors": [e for e in events if e.get("source") == "frontend" and e.get("severity") == "error"]
    }

    # Flow analysis
    user_flows = {}
    for session_id, session_events in sessions.items():
        if session_id == "no_session":
            continue

        flow = {
            "session_id": session_id,
            "user": session_events[0].get("user_email") if session_events else None,
            "start_time": session_events[0].get("timestamp") if session_events else None,
            "end_time": session_events[-1].get("timestamp") if session_events else None,
            "events_count": len(session_events),
            "pages_visited": list(set([e.get("path") for e in session_events if e.get("path")])),
            "api_calls": len([e for e in session_events if e.get("event_type") == "api_call"]),
            "errors": len([e for e in session_events if e.get("severity") in ["error", "critical"]])
        }
        user_flows[session_id] = flow

    return {
        "mcp_version": "1.0",
        "export_type": "orizon_debug_complete",
        "generated_at": datetime.utcnow().isoformat(),
        "system_info": {
            "debug_enabled": debug_config.enabled,
            "total_events": len(events),
            "total_sessions": len(sessions)
        },
        "analysis": {
            "errors_count": len(analysis["errors"]),
            "slow_requests_count": len(analysis["slow_requests"]),
            "total_api_calls": len(analysis["api_calls"]),
            "frontend_errors": len(analysis["frontend_errors"])
        },
        "user_flows": user_flows,
        "raw_events": events,
        "recommendations": generate_recommendations(analysis)
    }


def generate_recommendations(analysis: Dict) -> List[str]:
    """Genera raccomandazioni automatiche basate sui log"""
    recommendations = []

    if len(analysis["errors"]) > 10:
        recommendations.append(f"⚠️ Alto numero di errori rilevati ({len(analysis['errors'])}). Investigare le cause principali.")

    if len(analysis["slow_requests"]) > 5:
        recommendations.append(f"🐌 {len(analysis['slow_requests'])} richieste lente (>1s). Considerare ottimizzazione database o cache.")

    if len(analysis["frontend_errors"]) > 0:
        recommendations.append(f"🔴 {len(analysis['frontend_errors'])} errori frontend. Verificare console browser.")

    if not recommendations:
        recommendations.append("✅ Nessun problema critico rilevato.")

    return recommendations


@router.get("/stats")
async def get_debug_stats(
    current_user: User = Depends(require_role(UserRole.SUPERUSER))
):
    """Statistiche dettagliate per dashboard"""
    events = list(debug_events)

    # Last hour stats
    last_hour = datetime.utcnow() - timedelta(hours=1)
    recent_events = [
        e for e in events
        if get_event_timestamp(e) > last_hour
    ]

    return {
        "total_events": len(events),
        "last_hour_events": len(recent_events),
        "by_severity": {
            "debug": len([e for e in events if e.get("severity") == "debug"]),
            "info": len([e for e in events if e.get("severity") == "info"]),
            "warning": len([e for e in events if e.get("severity") == "warning"]),
            "error": len([e for e in events if e.get("severity") == "error"]),
            "critical": len([e for e in events if e.get("severity") == "critical"])
        },
        "by_source": {
            "frontend": len([e for e in events if e.get("source") == "frontend"]),
            "backend": len([e for e in events if e.get("source") == "backend"]),
            "database": len([e for e in events if e.get("source") == "database"]),
            "redis": len([e for e in events if e.get("source") == "redis"])
        },
        "avg_response_time_ms": sum([e.get("duration_ms", 0) for e in events if e.get("duration_ms")]) / len([e for e in events if e.get("duration_ms")]) if events and len([e for e in events if e.get("duration_ms")]) > 0 else 0
    }


# ============================================================================
# HIERARCHY DEBUG ENDPOINTS - Multi-Tenant System
# ============================================================================

@router.get("/hierarchy/tree")
async def get_hierarchy_tree(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SUPERUSER)),
):
    """
    🌳 Visualizza l'albero gerarchico completo degli utenti

    - SUPERUSER: vede l'intero albero partendo dalla root
    - Altri: vedono solo il proprio sub-albero

    Returns:
        Struttura ad albero con utenti e relazioni gerarchiche
    """
    from app.services.hierarchy_service import HierarchyService
    from sqlalchemy import select as sql_select
    
    # SUPERUSER può vedere l'intero albero partendo dalla root
    if current_user.role == UserRole.SUPERUSER:
        # Trova il nodo root (SUPERUSER senza created_by_id)
        query = sql_select(User).where(
            User.role == UserRole.SUPERUSER,
            User.created_by_id == None
        )
        result = await db.execute(query)
        root_user = result.scalar_one_or_none()

        if not root_user:
            # Se non c'è root, usa l'utente corrente
            root_user = current_user
    else:
        # Altri utenti vedono solo il proprio sub-albero
        root_user = current_user

    tree = await HierarchyService.get_hierarchy_tree(db, root_user)

    log_debug_event(
        event_type="hierarchy",
        severity="info",
        source="backend",
        message=f"Hierarchy tree requested by {current_user.email}",
        user_id=current_user.id,
        user_email=current_user.email
    )

    return {
        "tree": tree,
        "viewer": {
            "id": current_user.id,
            "email": current_user.email,
            "role": current_user.role.value
        },
        "description": "Albero gerarchico completo degli utenti"
    }


@router.get("/hierarchy/my-subordinates")
async def get_my_subordinates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    👥 Lista di tutti gli utenti subordinati nella gerarchia

    Returns:
        Lista di utenti subordinati con dettagli
    """
    from app.services.hierarchy_service import HierarchyService
    
    subordinates = await HierarchyService.get_subordinate_users(
        db, current_user, include_self=False
    )

    subordinates_data = [
        {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "created_by_id": user.created_by_id
        }
        for user in subordinates
    ]

    log_debug_event(
        event_type="hierarchy",
        severity="info",
        source="backend",
        message=f"User {current_user.email} has {len(subordinates)} subordinates",
        user_id=current_user.id,
        user_email=current_user.email
    )

    return {
        "total_subordinates": len(subordinates),
        "subordinates": subordinates_data,
        "viewer": {
            "id": current_user.id,
            "email": current_user.email,
            "role": current_user.role.value
        }
    }


@router.get("/hierarchy/my-path")
async def get_my_hierarchy_path(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    📍 Mostra il percorso gerarchico dall'utente root fino all'utente corrente

    Example: [SUPERUSER] -> [SUPER_ADMIN] -> [ADMIN] -> [USER (me)]

    Returns:
        Lista di utenti nel path gerarchico
    """
    from app.services.hierarchy_service import HierarchyService
    
    path = await HierarchyService.get_user_path(db, current_user)

    log_debug_event(
        event_type="hierarchy",
        severity="info",
        source="backend",
        message=f"Hierarchy path for {current_user.email}: {len(path)} levels",
        user_id=current_user.id,
        user_email=current_user.email
    )

    return {
        "path": path,
        "depth": len(path),
        "current_user": {
            "id": current_user.id,
            "email": current_user.email,
            "role": current_user.role.value
        },
        "description": "Percorso gerarchico dalla root all'utente corrente"
    }


@router.get("/hierarchy/role-levels")
async def get_role_levels(
    current_user: User = Depends(get_current_user),
):
    """
    📊 Mostra i livelli di tutti i ruoli nel sistema

    Returns:
        Mapping dei ruoli ai loro livelli numerici
    """
    from app.services.hierarchy_service import HierarchyService
    
    role_levels = {
        "SUPERUSER": HierarchyService.get_role_level(UserRole.SUPERUSER),
        "SUPER_ADMIN": HierarchyService.get_role_level(UserRole.SUPER_ADMIN),
        "ADMIN": HierarchyService.get_role_level(UserRole.ADMIN),
        "USER": HierarchyService.get_role_level(UserRole.USER),
    }

    current_level = HierarchyService.get_role_level(current_user.role)

    return {
        "role_levels": role_levels,
        "current_user_role": current_user.role.value,
        "current_user_level": current_level,
        "description": "Livelli gerarchici dei ruoli (più alto = più potere)"
    }


@router.get("/nodes/visibility")
async def get_nodes_visibility(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    🔍 Mostra tutti i nodi visibili all'utente corrente

    Basato sulla gerarchia:
    - SUPERUSER: tutti i nodi
    - SUPER_ADMIN: propri nodi + nodi di subordinati
    - ADMIN: propri nodi + nodi di subordinati
    - USER: solo propri nodi

    Returns:
        Lista di nodi visibili con info sul proprietario
    """
    from app.services.node_visibility_service import NodeVisibilityService
    from app.models.node import Node
    
    # Ottieni tutti i nodi visibili
    visible_nodes = await NodeVisibilityService.get_visible_nodes(
        db, current_user, include_inactive=True
    )

    # Ottieni statistiche
    stats = await NodeVisibilityService.get_nodes_statistics(db, current_user)

    # Prepara dati nodi con info proprietario
    nodes_data = []
    for node in visible_nodes:
        owner = await db.get(User, node.owner_id)
        nodes_data.append({
            "node": {
                "id": node.id,
                "name": node.name,
                "hostname": getattr(node, 'hostname', None),
                "status": node.status.value if hasattr(node, 'status') else None,
            },
            "owner": {
                "id": owner.id,
                "email": owner.email,
                "full_name": owner.full_name,
                "role": owner.role.value
            } if owner else None,
            "reason": "own_node" if node.owner_id == current_user.id else "subordinate_node"
        })

    log_debug_event(
        event_type="hierarchy",
        severity="info",
        source="backend",
        message=f"User {current_user.email} can see {len(visible_nodes)} nodes",
        user_id=current_user.id,
        user_email=current_user.email
    )

    return {
        "total_visible_nodes": len(visible_nodes),
        "nodes": nodes_data,
        "statistics": stats,
        "viewer": {
            "id": current_user.id,
            "email": current_user.email,
            "role": current_user.role.value
        },
        "description": "Nodi visibili in base alla gerarchia multi-tenant"
    }


@router.get("/nodes/{node_id}/full-info")
async def get_node_full_info(
    node_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    📋 Informazioni complete su un nodo specifico

    Include:
    - Dati del nodo
    - Info sul proprietario
    - Percorso gerarchico del proprietario
    - Motivo dell'accesso

    Returns:
        Informazioni dettagliate sul nodo
    """
    from app.services.node_visibility_service import NodeVisibilityService
    from app.models.node import Node
    
    node_info = await NodeVisibilityService.get_node_with_owner_info(
        db, current_user, node_id
    )

    if not node_info:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Non autorizzato ad accedere a questo nodo"
        )

    # Determina il motivo dell'accesso
    node = await db.get(Node, node_id)
    if node.owner_id == current_user.id:
        access_reason = "Proprietario del nodo"
    elif current_user.role == UserRole.SUPERUSER:
        access_reason = "SUPERUSER - accesso totale"
    else:
        access_reason = "Nodo di utente subordinato nella gerarchia"

    return {
        **node_info,
        "access_reason": access_reason,
        "viewer": {
            "id": current_user.id,
            "email": current_user.email,
            "role": current_user.role.value
        }
    }


@router.get("/hierarchy/can-manage")
async def check_role_management(
    target_role: str,
    current_user: User = Depends(get_current_user),
):
    """
    ✅ Verifica se l'utente corrente può gestire (creare/modificare) un determinato ruolo

    Query parameter:
    - target_role: Il ruolo target (superuser, super_admin, admin, user)

    Returns:
        True se può gestire il ruolo, False altrimenti
    """
    from app.services.hierarchy_service import HierarchyService
    
    # Converti stringa a UserRole
    role_mapping = {
        "superuser": UserRole.SUPERUSER,
        "super_admin": UserRole.SUPER_ADMIN,
        "admin": UserRole.ADMIN,
        "user": UserRole.USER,
    }

    target_role_enum = role_mapping.get(target_role.lower())

    if not target_role_enum:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ruolo non valido: {target_role}. Usa: superuser, super_admin, admin, user"
        )

    can_manage = HierarchyService.can_manage_role(current_user.role, target_role_enum)

    return {
        "current_user_role": current_user.role.value,
        "current_user_level": HierarchyService.get_role_level(current_user.role),
        "target_role": target_role_enum.value,
        "target_role_level": HierarchyService.get_role_level(target_role_enum),
        "can_manage": can_manage,
        "explanation": f"{'Può' if can_manage else 'Non può'} creare/gestire utenti con ruolo {target_role_enum.value}"
    }
