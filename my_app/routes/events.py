from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from db_models import Event, Attendee, EventType, UserEventTypeMembership
from utils import get_user_from_cookie
import logging
from datetime import date

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.post("/register/{event_id}")
def register_event(event_id: int, request: Request, db: Session = Depends(get_db)):
    """S'inscrire à un événement"""
    user = get_user_from_cookie(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Vérifier si déjà inscrit
    existing = db.query(Attendee).filter(
        Attendee.event_id == event_id,
        Attendee.user_id == user.id
    ).first()
    
    if existing:
        return RedirectResponse(url="/schedule?error=Already registered", status_code=302)
    
    # Récupérer l'événement et son type
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event_type = db.query(EventType).filter(EventType.id == event.event_type_id).first()
    if not event_type:
        raise HTTPException(status_code=500, detail="Event type not found")
    
    # Récupérer le membership du user pour ce type d'événement
    membership = db.query(UserEventTypeMembership).filter_by(
        user_id=user.id,
        event_type_id=event.event_type_id
    ).first()
    
    if not membership:
        return RedirectResponse(
            url="/schedule?error=No membership for this event type", 
            status_code=302
        )
    
    # Calculer places disponibles
    max_capacity = event_type.default_max_capacity
    available_spots = max_capacity - event.confirmed_count
    
    # Déterminer le statut selon les règles
    status = 'waiting'  # Par défaut
    credit_used = 0
    
    if membership.membership_type == 'full_member':
        # Full member : going si places, sinon waitlist
        if available_spots > 0:
            status = 'going'
        else:
            status = 'waiting'
    
    elif membership.membership_type == 'punch_card':
        # Vérifier les crédits
        if membership.remaining_credits is None or membership.remaining_credits <= 0:
            return RedirectResponse(
                url="/schedule?error=No credits remaining", 
                status_code=302
            )
        
        # Calculer jours avant event logique 7
        today = date.today()
        days_until_event = (event.date - today).days
        
        if days_until_event > 7:
            # Plus d'une semaine : waitlist automatique
            status = 'waiting'
        else:
            # Une semaine ou moins : going si places, sinon waitlist
            if available_spots > 0:
                status = 'going'
                credit_used = 1
            else:
                status = 'waiting'
    
    # Créer l'inscription
    attendee = Attendee(
        user_id=user.id, 
        event_id=event_id, 
        status=status,
        credit_used=credit_used
    )
    db.add(attendee)
    
    # Mettre à jour le compteur si going
    if status == 'going':
        event.confirmed_count += 1
        
        # Décrémenter crédits si punch_card
        if membership.membership_type == 'punch_card':
            membership.remaining_credits -= 1
    
    db.commit()
    
    logger.info(f"User {user.email} registered for event {event.date} with status {status}")
    return RedirectResponse(url="/schedule", status_code=302)

@router.post("/update-status/{event_id}/{new_status}")
def update_status(event_id: int, new_status: str, request: Request, db: Session = Depends(get_db)):
    """Changer le statut d'inscription (going <-> not_coming)"""
    user = get_user_from_cookie(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    attendee = db.query(Attendee).filter(
        Attendee.event_id == event_id,
        Attendee.user_id == user.id
    ).first()
    
    if not attendee:
        raise HTTPException(status_code=404, detail="Not registered for this event")
    
    old_status = attendee.status
    event = db.query(Event).filter(Event.id == event_id).first()
    event_type = db.query(EventType).filter(EventType.id == event.event_type_id).first()
    
    membership = db.query(UserEventTypeMembership).filter_by(
        user_id=user.id,
        event_type_id=event.event_type_id
    ).first()
    
    max_capacity = event_type.default_max_capacity
    
    # Si passe de "going" à autre chose, libérer une place
    if old_status == 'going' and new_status != 'going':
        event.confirmed_count -= 1
        
        if attendee.credit_used == 1 and membership:
            membership.remaining_credits += 1
            attendee.credit_used = 0
        
        # ========== LOGIQUE DE PROMOTION AVEC PRIORITÉ 7 JOURS ==========
        
        # Récupérer tous ceux en waiting avec leur membership
        waiting_list = db.query(Attendee, UserEventTypeMembership).join(
            UserEventTypeMembership, 
            (Attendee.user_id == UserEventTypeMembership.user_id) & 
            (UserEventTypeMembership.event_type_id == event.event_type_id)
        ).filter(
            Attendee.event_id == event_id,
            Attendee.status == 'waiting'
        ).all()
        
        if waiting_list:
            # Séparer en deux groupes selon date d'inscription vs date d'événement
            early_registrations = []  # Inscrits > 7 jours avant
            late_registrations = []   # Inscrits ≤ 7 jours avant
            
            for attendee_obj, membership_obj in waiting_list:
                # Calculer jours entre inscription et événement
                days_before_event = (event.date - attendee_obj.registered_at.date()).days
                
                if days_before_event > 7:
                    early_registrations.append((attendee_obj, membership_obj))
                else:
                    late_registrations.append((attendee_obj, membership_obj))
            
            # Trier groupe "early" : full_member d'abord, puis par date
            early_registrations.sort(
                key=lambda x: (
                    0 if x[1].membership_type == 'full_member' else 1,  # full_member prioritaire
                    x[0].registered_at  # puis par date
                )
            )
            
            # Trier groupe "late" : uniquement par date
            late_registrations.sort(key=lambda x: x[0].registered_at)
            
            # Concaténer : early d'abord, puis late
            sorted_waiting = early_registrations + late_registrations
            
            # Promouvoir le premier de la liste triée
            if sorted_waiting:
                attendee_to_promote, membership_to_check = sorted_waiting[0]
                attendee_to_promote.status = 'going'
                event.confirmed_count += 1
                
                # Consommer crédit si punch_card
                if membership_to_check.membership_type == 'punch_card':
                    if membership_to_check.remaining_credits and membership_to_check.remaining_credits > 0:
                        membership_to_check.remaining_credits -= 1
                        attendee_to_promote.credit_used = 1
                
                logger.info(f"User {attendee_to_promote.user_id} promoted from waiting list for event {event.date}")
    
    # Si passe à "going", prendre une place
    elif old_status != 'going' and new_status == 'going':
        if event.confirmed_count < max_capacity:
            event.confirmed_count += 1
            
            if membership and membership.membership_type == 'punch_card':
                if membership.remaining_credits and membership.remaining_credits > 0:
                    membership.remaining_credits -= 1
                    attendee.credit_used = 1
                else:
                    new_status = 'waiting'
                    event.confirmed_count -= 1
        else:
            new_status = 'waiting'
    
    attendee.status = new_status
    db.commit()
    
    logger.info(f"User {user.email} changed status to {new_status} for event {event.date}")
    return RedirectResponse(url="/schedule", status_code=302)

@router.get("/schedule", response_class=HTMLResponse)
def schedule_page(request: Request, db: Session = Depends(get_db)):
    """Page listant tous les événements"""
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    from services.event_service import EventService
    from services.user_service import UserService
    event_service = EventService()
    user_service=UserService()
    events = event_service.get_events_for_schedule(db, user.id)
    memberships = user_service.get_user_memberships(db, user.id)  # Nouveau

    return templates.TemplateResponse("schedule_test3.html", {
        "request": request,
        "user": user,
        "events": events,
        "memberships": memberships  # Passer au template

    })

@router.get("/event/{event_id}", response_class=HTMLResponse)
def event_detail_page(event_id: int, request: Request, db: Session = Depends(get_db)):
    """Page de détail d'un événement"""
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event_type = db.query(EventType).filter(EventType.id == event.event_type_id).first()
    max_capacity = event_type.default_max_capacity
    
    attendee = db.query(Attendee).filter(
        Attendee.event_id == event_id,
        Attendee.user_id == user.id
    ).first()
    
    waitlist_count = db.query(Attendee).filter(
        Attendee.event_id == event_id,
        Attendee.status == 'waiting'
    ).count()
    
    event_data = {
        'id': event.id,
        'date': event.date,
        'max_spots': max_capacity,
        'confirmed_count': event.confirmed_count,
        'available_spots': max_capacity - event.confirmed_count,
        'waitlist_count': waitlist_count,
        'user_status': attendee.status if attendee else None
    }
    
    return templates.TemplateResponse("event_detail.html", {
        "request": request,
        "user": user,
        "event": event_data
    })

@router.get("/event/{event_id}/waitlist", response_class=HTMLResponse)
def waitlist_page(event_id: int, request: Request, db: Session = Depends(get_db)):
    """Page affichant la liste d'attente d'un événement"""
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    from services.event_service import get_waitlist_users
    waitlist = get_waitlist_users(db, event_id)
    
    return templates.TemplateResponse("waitlist.html", {
        "request": request,
        "user": user,
        "event": event,
        "waitlist": waitlist
    })