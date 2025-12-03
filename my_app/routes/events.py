from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from services.auth_service import AuthService
from services.event_service import EventService
from datetime import date

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/schedule")
def schedule_page(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Page principale affichant les événements à venir.
    
    Logique:
    1. Vérifier que l'utilisateur est authentifié (JWT cookie)
    2. Récupérer ses memberships pour chaque event_type
    3. Récupérer tous les événements futurs avec son statut
    4. Appliquer les règles d'affichage (restrictions punch_card)
    5. Render le template
    """
    
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
    
    
    # 2. RÉCUPÉRER LES MEMBERSHIPS
    event_service = EventService(db)
    memberships = event_service.get_user_memberships_formatted(user.id)
    
    
    # 3. RÉCUPÉRER LES ÉVÉNEMENTS
    events = event_service.get_events_for_schedule(user.id)
    
    
    # 4. APPLIQUER LES RÈGLES D'AFFICHAGE
    today = date.today()
    
    for event in events:
        # Trouver le membership correspondant à cet événement
        event_type_id = event['event_type_id']
        
        # Chercher dans memberships quel event_X correspond
        user_membership = None
        for key, membership in memberships.items():
            if membership['id'] == event_type_id:
                user_membership = membership
                break
        
        # Si pas de membership (ne devrait pas arriver), skip
        if not user_membership:
            continue
        
        # Calculer le nombre de jours avant l'événement
        event_date = event['date']
        if isinstance(event_date, str):
            event_date = date.fromisoformat(event_date)
        elif hasattr(event_date, 'date'):
            event_date = event_date.date()
        
        days_until_event = (event_date - today).days
        
        # RÈGLES D'AFFICHAGE DU STATUT
        # Si déjà inscrit, on garde son statut actuel
        if event['user_status'] in ['confirmed', 'waiting']:
            # Pas besoin de changer quoi que ce soit
            pass
        
        # Si full_member, toujours RSVP disponible
        elif user_membership['type'] == 'full_member':
            event['user_status'] = 'available'  # Nouveau statut pour template
        
        # Si punch_card
        elif user_membership['type'] == 'punch_card':
            # Vérifier les crédits
            remaining = user_membership['remaining_credits']
            
            if remaining == 0:
                event['user_status'] = 'no_credits'
            elif days_until_event > 7:
                event['user_status'] = 'full_member_priority'
            else:
                event['user_status'] = 'available'
    
    
    # 5. RENDER LE TEMPLATE
    return templates.TemplateResponse("schedule.html", {
        "request": request,
        "user": user,
        "memberships": memberships,
        "events": events
    })

@router.get("/event/{event_id}")
def event_page(
    event_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Page de détails d'un événement avec possibilité de s'inscrire
    
    Restrictions:
    - Punch card ne peut pas accéder si événement > 7 jours
    """
    
    # 1. VÉRIFIER L'AUTHENTIFICATION
    token = request.cookies.get("access_token")
    
    if not token:
        return RedirectResponse(url="/auth/login?error=Please login first", status_code=303)
    
    auth_service = AuthService(db)
    
    try:
        user = auth_service.get_current_user(token)
    except ValueError:
        return RedirectResponse(url="/auth/login?error=Session expired", status_code=303)
    
    
    # 2. RÉCUPÉRER LES DÉTAILS DE L'ÉVÉNEMENT
    event_service = EventService(db)
    event_data = event_service.get_event_details(event_id, user.id)
    
    if not event_data:
        return RedirectResponse(url="/schedule?error=Event not found", status_code=303)
    
    
    # 3. VÉRIFIER RESTRICTION 7 JOURS POUR PUNCH CARD
    is_punch_card = event_data['user_membership']['type'] == 'punch_card'
    days_until = event_data['event']['days_until']
    
    if is_punch_card and days_until > 7:
        # Punch card ne peut pas accéder à cette page
        return RedirectResponse(
            url="/schedule?error=This event is not yet available for punch card users",
            status_code=303
        )
    
    
    # 4. DÉTERMINER QUEL MESSAGE/BOUTONS AFFICHER
    user_status = event_data['user_status']
    membership = event_data['user_membership']
    
    # Calculer si le user peut s'inscrire
    can_register = True
    message = None
    
    if is_punch_card and membership['remaining_credits'] == 0:
        can_register = False
        message = "Out of credits - Purchase more to register"
    
    event_data['can_register'] = can_register
    event_data['message'] = message
    
    
    # 5. RENDER LE TEMPLATE
    return templates.TemplateResponse("event.html", {
        "request": request,
        "user": user,
        "event": event_data['event'],
        "event_type": event_data['event_type'],
        "user_membership": event_data['user_membership'],
        "user_status": event_data['user_status'],
        "confirmed_participants": event_data['confirmed_participants'],
        "waitlist": event_data['waitlist'],
        "can_register": event_data['can_register'],
        "message": event_data['message']
    })