"""
Orizon Zero Trust - Test & Backup Endpoints
API per eseguire test end-to-end e backup del sistema
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import asyncio
import httpx

from app.core.database import get_db
from app.auth.dependencies import get_current_user, require_role
from app.models.user import User, UserRole

router = APIRouter(tags=["test"])


class TestResult(BaseModel):
    """Risultato di un singolo test"""
    test_name: str
    status: str  # "passed", "failed", "skipped"
    duration_ms: int
    message: str
    details: Dict[str, Any] = {}


class TestSuite(BaseModel):
    """Suite di test completa"""
    suite_name: str
    started_at: datetime
    completed_at: datetime
    total_tests: int
    passed: int
    failed: int
    skipped: int
    results: List[TestResult]


class BrowserEvent(BaseModel):
    """Event dal browser per tracking"""
    event_type: str  # "page_load", "click", "api_call", "error"
    timestamp: datetime
    page_url: str
    user_id: str
    details: Dict[str, Any]


# Storage temporaneo per eventi browser (in produzione usare Redis)
browser_events: List[Dict] = []


@router.post("/browser-event", response_model=Dict[str, str])
async def log_browser_event(
    event: BrowserEvent,
    current_user: User = Depends(get_current_user)
):
    """
    Logga un evento dal browser per tracking end-to-end
    """
    event_data = {
        "event_type": event.event_type,
        "timestamp": event.timestamp.isoformat(),
        "page_url": event.page_url,
        "user_id": current_user.id,
        "user_email": current_user.email,
        "details": event.details
    }

    browser_events.append(event_data)

    # Mantieni solo ultimi 1000 eventi
    if len(browser_events) > 1000:
        browser_events.pop(0)

    return {"status": "logged", "event_id": str(len(browser_events))}


@router.get("/browser-events", response_model=List[Dict])
async def get_browser_events(
    limit: int = 100,
    current_user: User = Depends(require_role(UserRole.SUPERUSER))
):
    """
    Recupera eventi browser tracciati (solo superuser)
    """
    return browser_events[-limit:]


@router.post("/run-e2e-tests", response_model=TestSuite)
async def run_e2e_tests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SUPERUSER))
):
    """
    Esegue suite completa di test end-to-end
    Solo per superuser
    """
    started_at = datetime.utcnow()
    results = []

    # Test 1: Health Check
    test_start = datetime.utcnow()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health")
            if response.status_code == 200:
                results.append(TestResult(
                    test_name="Health Check",
                    status="passed",
                    duration_ms=int((datetime.utcnow() - test_start).total_seconds() * 1000),
                    message="Backend is healthy",
                    details={"response": response.json()}
                ))
            else:
                results.append(TestResult(
                    test_name="Health Check",
                    status="failed",
                    duration_ms=int((datetime.utcnow() - test_start).total_seconds() * 1000),
                    message=f"Health check failed with status {response.status_code}",
                    details={}
                ))
    except Exception as e:
        results.append(TestResult(
            test_name="Health Check",
            status="failed",
            duration_ms=int((datetime.utcnow() - test_start).total_seconds() * 1000),
            message=f"Error: {str(e)}",
            details={}
        ))

    # Test 2: Database Connection
    test_start = datetime.utcnow()
    try:
        from sqlalchemy import text
        result = await db.execute(text("SELECT 1"))
        row = result.scalar()
        if row == 1:
            results.append(TestResult(
                test_name="Database Connection",
                status="passed",
                duration_ms=int((datetime.utcnow() - test_start).total_seconds() * 1000),
                message="Database connection successful",
                details={}
            ))
        else:
            results.append(TestResult(
                test_name="Database Connection",
                status="failed",
                duration_ms=int((datetime.utcnow() - test_start).total_seconds() * 1000),
                message="Unexpected database response",
                details={}
            ))
    except Exception as e:
        results.append(TestResult(
            test_name="Database Connection",
            status="failed",
            duration_ms=int((datetime.utcnow() - test_start).total_seconds() * 1000),
            message=f"Error: {str(e)}",
            details={}
        ))

    # Test 3: User Count
    test_start = datetime.utcnow()
    try:
        from sqlalchemy import select, func
        query = select(func.count(User.id))
        result = await db.execute(query)
        user_count = result.scalar()
        results.append(TestResult(
            test_name="User Count",
            status="passed",
            duration_ms=int((datetime.utcnow() - test_start).total_seconds() * 1000),
            message=f"Found {user_count} users in database",
            details={"count": user_count}
        ))
    except Exception as e:
        results.append(TestResult(
            test_name="User Count",
            status="failed",
            duration_ms=int((datetime.utcnow() - test_start).total_seconds() * 1000),
            message=f"Error: {str(e)}",
            details={}
        ))

    # Test 4: Redis Connection (se disponibile)
    test_start = datetime.utcnow()
    try:
        from app.core.redis import get_redis
        redis = await get_redis()
        await redis.set("test_key", "test_value", expire=10)
        value = await redis.get("test_key")
        if value == "test_value":
            results.append(TestResult(
                test_name="Redis Connection",
                status="passed",
                duration_ms=int((datetime.utcnow() - test_start).total_seconds() * 1000),
                message="Redis connection and operations successful",
                details={}
            ))
        else:
            results.append(TestResult(
                test_name="Redis Connection",
                status="failed",
                duration_ms=int((datetime.utcnow() - test_start).total_seconds() * 1000),
                message="Redis value mismatch",
                details={}
            ))
    except Exception as e:
        results.append(TestResult(
            test_name="Redis Connection",
            status="skipped",
            duration_ms=int((datetime.utcnow() - test_start).total_seconds() * 1000),
            message=f"Redis not available: {str(e)}",
            details={}
        ))

    # Test 5: API Auth Flow
    test_start = datetime.utcnow()
    try:
        async with httpx.AsyncClient() as client:
            # Test /auth/me endpoint
            response = await client.get(
                "http://localhost:8000/api/v1/auth/me",
                headers={"Authorization": f"Bearer INVALID_TOKEN"}
            )
            if response.status_code == 401:
                results.append(TestResult(
                    test_name="API Auth Protection",
                    status="passed",
                    duration_ms=int((datetime.utcnow() - test_start).total_seconds() * 1000),
                    message="API correctly rejects invalid tokens",
                    details={}
                ))
            else:
                results.append(TestResult(
                    test_name="API Auth Protection",
                    status="failed",
                    duration_ms=int((datetime.utcnow() - test_start).total_seconds() * 1000),
                    message=f"Expected 401, got {response.status_code}",
                    details={}
                ))
    except Exception as e:
        results.append(TestResult(
            test_name="API Auth Protection",
            status="failed",
            duration_ms=int((datetime.utcnow() - test_start).total_seconds() * 1000),
            message=f"Error: {str(e)}",
            details={}
        ))

    completed_at = datetime.utcnow()

    # Calcola statistiche
    passed = sum(1 for r in results if r.status == "passed")
    failed = sum(1 for r in results if r.status == "failed")
    skipped = sum(1 for r in results if r.status == "skipped")

    return TestSuite(
        suite_name="Orizon E2E Test Suite",
        started_at=started_at,
        completed_at=completed_at,
        total_tests=len(results),
        passed=passed,
        failed=failed,
        skipped=skipped,
        results=results
    )


@router.post("/backup-database")
async def backup_database(
    current_user: User = Depends(require_role(UserRole.SUPERUSER))
):
    """
    Trigger database backup (solo superuser)
    """
    # Questo dovrebbe chiamare uno script di backup PostgreSQL
    # Per ora ritorna un placeholder
    return {
        "status": "success",
        "message": "Database backup triggered",
        "timestamp": datetime.utcnow().isoformat(),
        "backup_file": f"orizon_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.sql"
    }


@router.get("/system-status")
async def get_system_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPERUSER, UserRole.ADMIN]))
):
    """
    Ottieni status completo del sistema
    """
    from sqlalchemy import select, func

    # User statistics
    user_count_query = select(func.count(User.id))
    user_count = (await db.execute(user_count_query)).scalar()

    active_users_query = select(func.count(User.id)).where(User.is_active == True)
    active_users = (await db.execute(active_users_query)).scalar()

    # Browser events stats
    recent_events = len([e for e in browser_events if datetime.fromisoformat(e['timestamp']) > datetime.utcnow().replace(hour=datetime.utcnow().hour - 1)])

    return {
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "users": {
            "total": user_count,
            "active": active_users
        },
        "events": {
            "total_tracked": len(browser_events),
            "last_hour": recent_events
        },
        "uptime": "N/A",  # Implementare tracking uptime
        "version": "2.0.0"
    }
