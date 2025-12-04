from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from services.auth_service import AuthService
from services.registration_service import RegistrationService

router = APIRouter()


@router.post("/event/{event_id}/register")
def register_for_event(
    event_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    # TON CODE ICI
     # 1. VÉRIFIER L'AUTHENTIFICATION
    token = request.cookies.get("access_token")
    
    if not token:
        # Pas de token -> rediriger vers login
        return RedirectResponse(url="/login?error=Please login first", status_code=303)
    
    auth_service = AuthService(db)

    
    try:
        # Récupérer le user depuis le token
        user = auth_service.get_current_user(token)
    except ValueError:
        # Token invalide/expiré -> rediriger vers login
        return RedirectResponse(url="/login?error=Session expired", status_code=303)
    
    registration_service = RegistrationService(db)

    try:
        result = registration_service.register_user(user.id, event_id)  # ← user.id
        # Succès → rediriger vers la page event
        return RedirectResponse(url=f"/event/{event_id}", status_code=303)
    except ValueError as e:
        # Erreur métier → rediriger avec message d'erreur
        error_message = str(e)
        return RedirectResponse(
            url=f"/event/{event_id}?error={error_message}", 
            status_code=303
        )



@router.post("/event/{event_id}/cancel")
def cancel_registration(
    event_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
         # 1. VÉRIFIER L'AUTHENTIFICATION
    token = request.cookies.get("access_token")
    
    if not token:
        # Pas de token -> rediriger vers login
        return RedirectResponse(url="/login?error=Please login first", status_code=303)
    
    auth_service = AuthService(db)

    
    try:
        # Récupérer le user depuis le token
        user = auth_service.get_current_user(token)
    except ValueError:
        # Token invalide/expiré -> rediriger vers login
        return RedirectResponse(url="/login?error=Session expired", status_code=303)
    
    registration_service = RegistrationService(db)

    try:
        result = registration_service.unregister_user(user.id, event_id)  # ← user.id
        # Succès → rediriger vers la page event
        return RedirectResponse(url=f"/event/{event_id}", status_code=303)
    except ValueError as e:
        # Erreur métier → rediriger avec message d'erreur
        error_message = str(e)
        return RedirectResponse(
            url=f"/event/{event_id}?error={error_message}", 
            status_code=303
        )

@router.post("/event/{event_id}/not-going")
def mark_not_going(
    event_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    # 1. Authentification
    token = request.cookies.get("access_token")
    
    if not token:
        return RedirectResponse(url="/login?error=Please login first", status_code=303)
    
    auth_service = AuthService(db)
    
    try:
        user = auth_service.get_current_user(token)
    except ValueError:
        return RedirectResponse(url="/login?error=Session expired", status_code=303)
    
    # 2. Appeler le service
    registration_service = RegistrationService(db)
    
    try:
        result = registration_service.mark_not_going(user.id, event_id)
        return RedirectResponse(url=f"/event/{event_id}", status_code=303)
    
    except ValueError as e:
        error_message = str(e)
        return RedirectResponse(
            url=f"/event/{event_id}?error={error_message}", 
            status_code=303
        )
