"""
Orizon Zero Trust - Audit Logger
Utility per registrare azioni utente nel sistema di audit
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user_permissions import AccessLog, ServiceType
from app.models.user import User
import uuid
from datetime import datetime
from typing import Optional


async def log_user_action(
    db: AsyncSession,
    user_id: str,
    action: str,
    source_ip: str,
    node_id: Optional[str] = None,
    service_type: ServiceType = ServiceType.HTTP,
    success: bool = True,
    error_message: Optional[str] = None,
    user_agent: Optional[str] = None,
    session_id: Optional[str] = None
):
    """
    Registra un'azione utente nel log di audit
    
    Args:
        db: Sessione database
        user_id: ID dell'utente
        action: Tipo di azione (login, logout, create_user, update_user, delete_user, grant_permission, etc.)
        source_ip: IP sorgente
        node_id: ID del nodo (opzionale)
        service_type: Tipo di servizio
        success: Se l'azione è andata a buon fine
        error_message: Messaggio di errore (se success=False)
        user_agent: User agent del browser
        session_id: ID sessione
    """
    
    try:
        log_entry = AccessLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            node_id=node_id,
            service_type=service_type,
            action=action,
            source_ip=source_ip,
            user_agent=user_agent,
            session_id=session_id,
            success=success,
            error_message=error_message,
            timestamp=datetime.utcnow()
        )
        
        db.add(log_entry)
        await db.commit()
        
    except Exception as e:
        print(f"Error logging action: {e}")
        # Non blocchiamo l'operazione principale se il logging fallisce
        await db.rollback()
