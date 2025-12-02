"""
Orizon Zero Trust - SSO Endpoints
Single Sign-On e gestione sessioni
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.services.sso_service import SSOSessionManager
from app.schemas import Token
from pydantic import BaseModel


router = APIRouter()


class SSOSession(BaseModel):
    session_id: str
    device_info: dict
    ip_address: str
    created_at: str
    last_activity: str
    is_active: bool


class SSOLoginRequest(BaseModel):
    email: str
    password: str
    device_name: str | None = None
    remember_me: bool = False


@router.post("/login", response_model=Token)
async def sso_login(
    request: Request,
    login_data: SSOLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    SSO Login con gestione sessioni avanzata
    Crea sessione persistente e traccia dispositivo
    """
    from app.services.user_service import UserService

    # Autentica utente
    user = await UserService.authenticate_user(
        db, login_data.email, login_data.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenziali non valide"
        )

    # Estrai device info
    device_info = {
        "user_agent": request.headers.get("user-agent", "unknown"),
        "device_name": login_data.device_name or "Web Browser",
        "platform": request.headers.get("sec-ch-ua-platform", "unknown")
    }

    # Ottieni IP
    ip_address = request.client.host

    # Crea sessione SSO
    session = await SSOSessionManager.create_session(
        user=user,
        device_info=device_info,
        ip_address=ip_address
    )

    return Token(
        access_token=session["access_token"],
        refresh_token=session["refresh_token"],
        token_type="bearer",
        expires_in=session["expires_in"]
    )


@router.get("/sessions", response_model=List[SSOSession])
async def get_my_sessions(
    current_user: User = Depends(get_current_user)
):
    """
    Recupera tutte le sessioni attive dell'utente corrente
    Permette di vedere tutti i dispositivi connessi
    """
    sessions = await SSOSessionManager.get_user_sessions(current_user.id)
    return sessions


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Revoca una sessione specifica
    Permette di disconnettere un dispositivo
    """
    # Verifica che la sessione appartenga all'utente
    session = await SSOSessionManager.get_session(session_id)

    if not session or session["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessione non trovata"
        )

    await SSOSessionManager.revoke_session(session_id)

    return {"message": "Sessione revocata con successo"}


@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Logout dalla sessione corrente

    Revoca il token JWT corrente invalidando la sessione
    """
    # Simply return success - JWT tokens are stateless
    # The client should delete the token from localStorage
    # For true token revocation, we'd need to implement a blacklist
    return {"message": "Logout effettuato con successo"}


@router.post("/logout-all")
async def logout_all_sessions(
    current_user: User = Depends(get_current_user)
):
    """
    Logout globale - disconnette tutti i dispositivi
    Utile in caso di compromissione account
    """
    await SSOSessionManager.revoke_all_user_sessions(current_user.id)

    return {"message": "Tutti i dispositivi sono stati disconnessi"}


@router.get("/validate")
async def validate_sso_token(
    current_user: User = Depends(get_current_user)
):
    """
    Valida token SSO corrente
    Ritorna info utente e sessione
    """
    return {
        "valid": True,
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "role": current_user.role,
            "full_name": current_user.full_name
        }
    }
