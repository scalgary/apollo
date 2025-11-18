# backend/services/event_service.py
from sqlalchemy.orm import Session
from datetime import datetime
from db_models import Event, Attendee
from utils import load_events

def import_events_from_csv(db: Session):
    """Import events from CSV into database"""
    events_data = load_events()
    imported_count = 0
    
    for event_data in events_data:
        try:
            event_id = int(event_data['id'])  # ← Convertir string en int
            
            # Check if event already exists
            existing = db.query(Event).filter(Event.id == event_id).first()
            
            if not existing:
                event = Event(
                    id=event_id,
                    date=datetime.strptime(event_data['date'], '%Y-%m-%d').date(),
                    max_spots=int(event_data['max_spots']),
                    confirmed_count=0
                )
                db.add(event)
                imported_count += 1
                
        except Exception as e:
            print(f"Error importing event {event_data.get('id')}: {e}")
            continue
    
    db.commit()
    print(f"✓ Imported {imported_count}/{len(events_data)} events from CSV")

def get_all_events_with_user_status(db: Session, user_id: int):
    """Récupère tous les événements avec le statut de l'utilisateur"""
    events = db.query(Event).all()
    result = []
    
    for event in events:
        # Chercher si l'utilisateur est inscrit
        attendee = db.query(Attendee).filter(
            Attendee.event_id == event.id,
            Attendee.user_id == user_id
        ).first()
        
        # Compter les personnes en waitlist
        waitlist_count = db.query(Attendee).filter(
            Attendee.event_id == event.id,
            Attendee.status == 'waiting'
        ).count()
        
        # Construire le résultat
        result.append({
            'id': event.id,
            'date': event.date,
            'max_spots': event.max_spots,
            'confirmed_count': event.confirmed_count,
            'available_spots': event.max_spots - event.confirmed_count,
            'waitlist_count': waitlist_count,
            'user_status': attendee.status if attendee else None
        })
    
    return result


def get_waitlist_users(db: Session, event_id: int):
    """Récupère la liste des utilisateurs en waitlist avec leur position"""
    from db_models import User
    
    # Récupérer les attendees en waitlist, ordonnés par date d'inscription
    waitlist = db.query(Attendee, User).join(
        User, Attendee.user_id == User.id
    ).filter(
        Attendee.event_id == event_id,
        Attendee.status == 'waiting'
    ).order_by(Attendee.registered_at).all()
    
    # Créer la liste avec position
    result = []
    for position, (attendee, user) in enumerate(waitlist, start=1):
        result.append({
            'position': position,
            'email': user.email,
            'registered_at': attendee.registered_at
        })
    
    return result