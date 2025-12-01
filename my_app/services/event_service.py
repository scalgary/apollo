from sqlalchemy.orm import Session
from datetime import datetime, date
from db_models import User, Event, Attendee, EventType
from utils import load_events, load_event_types


class EventService:
    """Service pour gérer les événements"""
    
    def __init__(self):
        pass
    
    from utils import load_events, load_event_types  # Ajoute load_event_types


    
    def import_event_types_from_csv(self, db: Session):
        """Import event types from CSV (doit être appelé AVANT import_events)"""
        event_types_data = load_event_types()
        imported_count = 0
        
        for et_data in event_types_data:
            try:
                # Vérifier si existe déjà
                existing = db.query(EventType).filter(
                    EventType.name == et_data['name']
                ).first()
                
                if not existing:
                    event_type = EventType(
                        name=et_data['name'],
                        display_name=et_data['display_name'],
                        default_location=et_data['default_location'],
                        default_time_start=et_data['default_time_start'],
                        default_time_end=et_data['default_time_end'],
                        default_max_capacity=et_data['default_max_capacity'],
                        color=et_data['color']
                    )
                    db.add(event_type)
                    imported_count += 1
                else:
                    # Update si changements
                    existing.display_name = et_data['display_name']
                    existing.default_location = et_data['default_location']
                    existing.default_time_start = et_data['default_time_start']
                    existing.default_time_end = et_data['default_time_end']
                    existing.default_max_capacity = et_data['default_max_capacity']
                    existing.color = et_data['color']
            
            except Exception as e:
                print(f"Error importing event type {et_data}: {e}")
                continue
        
        db.commit()
        return imported_count
    
    # Garde import_events_from_csv tel quel (il est déjà bon)

    def import_events_from_csv(self, db: Session):
        """Import events from CSV into database"""
        events_data = load_events()
        imported_count = 0
        
        # Mapper event_type_name vers event_type_id
        event_types = {et.name: et.id for et in db.query(EventType).all()}
    
        for event_data in events_data:
            try:
                event_type_name = event_data['event_type_name']
                
                if event_type_name not in event_types:
                    print(f"Event type '{event_type_name}' not found, skipping")
                    continue
                
                event_date = datetime.strptime(event_data['date'], '%Y-%m-%d').date()
                
                # Check if event already exists
                existing = db.query(Event).filter(Event.date == event_date).first()
                
                if not existing:
                    event = Event(
                        event_type_id=event_types[event_type_name],
                        date=event_date,
                        confirmed_count=0
                    )
                    db.add(event)
                    imported_count += 1
                
            except Exception as e:
                print(f"Error importing event {event_data}: {e}")
                continue
    
        db.commit()
        return imported_count

    def get_all_events_with_user_status(self, db: Session, user_id: int):
        """Récupère tous les événements avec le statut de l'utilisateur"""
        today = date.today()
        
        # Joindre Event avec EventType pour avoir default_max_capacity
        events = db.query(Event, EventType).join(
            EventType, Event.event_type_id == EventType.id
        ).filter(Event.date >= today).order_by(Event.date).all()
        
        result = []
    
        for event, event_type in events:
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
            
            max_capacity = event_type.default_max_capacity
        
            # Construire le résultat
            result.append({
                'id': event.id,
                'date': event.date,
                'event_type_name': event_type.name,
                'event_type_display': event_type.display_name,
                'max_spots': max_capacity,
                'confirmed_count': event.confirmed_count,
                'available_spots': max_capacity - event.confirmed_count,
                'waitlist_count': waitlist_count,
                'user_status': attendee.status if attendee else None
            })
    
        return result
    
    def get_events_for_schedule(self, db: Session, user_id: int):
        """Récupère les événements formatés pour la page schedule"""
        
        # Récupère les événements
        events = self.get_all_events_with_user_status(db, user_id)
        
        # Pour chaque événement, ajoute le formatage
        for event in events:
            date_obj = event['date']
            
            # Gérer différents types de date
            if isinstance(date_obj, str):
                try:
                    date_obj = datetime.fromisoformat(date_obj)
                    if hasattr(date_obj, 'date'):
                        date_obj = date_obj.date()
                except:
                    date_obj = datetime.strptime(date_obj[:10], '%Y-%m-%d').date()
            elif hasattr(date_obj, 'date'):
                date_obj = date_obj.date()
            
            # Ajoute les versions formatées
            event['month'] = date_obj.strftime('%b')
            event['day'] = date_obj.strftime('%d')
            event['weekday'] = date_obj.strftime('%a')
        
        return events

    def get_waitlist_users(self, db: Session, event_id: int):
        """Récupère la liste des utilisateurs en waitlist avec leur position"""
        
        waitlist = db.query(Attendee, User).join(
            User, Attendee.user_id == User.id
        ).filter(
            Attendee.event_id == event_id,
            Attendee.status == 'waiting'
        ).order_by(Attendee.registered_at).all()
        
        result = []
        for position, (attendee, user) in enumerate(waitlist, start=1):
            result.append({
                'position': position,
                'email': user.email,
                'registered_at': attendee.registered_at
            })
        
        return result