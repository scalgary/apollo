from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from db_models import Event, Attendee
from utils import get_user_from_cookie
import logging

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
    
    # VÉRIFIER LES CRÉDITS pour punch_card AVANT toute inscription
    if user.membership_type == 'punch_card':
        if user.remaining_credits is None or user.remaining_credits <= 0:
            return RedirectResponse(url="/event/{}?error=No credits remaining".format(event_id), status_code=302)
    
    # Obtenir l'événement
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Déterminer le statut (going ou waiting list)
    status = 'going' if event.confirmed_count < event.max_spots else 'waiting'
    
    # Créer l'inscription
    attendee = Attendee(user_id=user.id, event_id=event_id, status=status)
    db.add(attendee)
    
    # Mettre à jour le compteur
    if status == 'going':
        event.confirmed_count += 1
    
    # DÉCRÉMENTER LES CRÉDITS pour punch_card
    if user.membership_type == 'punch_card' and user.remaining_credits is not None:
        user.remaining_credits -= 1
    
    db.commit()
    logger.info(f"User {user.email} registered for event {event.date} with status {status}")
    return RedirectResponse(url="/schedule", status_code=302)

@router.post("/update-status/{event_id}/{new_status}")
def update_status(event_id: int, new_status: str, request: Request, db: Session = Depends(get_db)):
    """Changer le statut d'inscription (going <-> not_coming)"""
    user = get_user_from_cookie(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Trouver l'inscription
    attendee = db.query(Attendee).filter(
        Attendee.event_id == event_id,
        Attendee.user_id == user.id
    ).first()
    
    if not attendee:
        raise HTTPException(status_code=404, detail="Not registered for this event")
    
    old_status = attendee.status
    event = db.query(Event).filter(Event.id == event_id).first()
    
    # Si passe de "going" à autre chose, libérer une place
    if old_status == 'going' and new_status != 'going':
        event.confirmed_count -= 1
        
        # Promouvoir quelqu'un de la waiting list
        waiting = db.query(Attendee).filter(
            Attendee.event_id == event_id,
            Attendee.status == 'waiting'
        ).order_by(Attendee.registered_at).first()
        
        if waiting:
            waiting.status = 'going'
            event.confirmed_count += 1
            logger.info(f"User {waiting.user_id} promoted from waiting list for event {event.date}")
    
    # Si passe à "going", prendre une place
    elif old_status != 'going' and new_status == 'going':
        if event.confirmed_count < event.max_spots:
            event.confirmed_count += 1
        else:
            # Pas de place, forcer en waiting
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
    
    from services.event_service import get_all_events_with_user_status
    events = get_all_events_with_user_status(db, user.id)
    
    return templates.TemplateResponse("schedule.html", {
        "request": request,
        "user": user,
        "events": events
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
        'max_spots': event.max_spots,
        'confirmed_count': event.confirmed_count,
        'available_spots': event.max_spots - event.confirmed_count,
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