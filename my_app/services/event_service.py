# my_app/services/event_service.py
from sqlalchemy.orm import Session
from datetime import datetime
from db_models import User, Event, Attendee
from utils import load_events



class EventService:
    """Service pour gérer les événements"""
    
    def __init__(self):
        """Cette fonction s'exécute quand on crée un EventService"""
        pass  # On ne fait rien pour l'instant
    def import_events_from_csv(self, db: Session):
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

    def get_all_events_with_user_status(self, db: Session, user_id: int):
        from datetime import datetime, date


        today = date.today()  # Ex: date(2025, 11, 18)
        """Récupère tous les événements avec le statut de l'utilisateur"""
        events = db.query(Event).filter(Event.date >= today).order_by(Event.date).all()
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
    def get_events_for_schedule(self, db: Session, user_id: int):
        """Récupère les événements formatés pour la page schedule"""
        
        # Étape 1 : Récupère les événements
        events = self.get_all_events_with_user_status(db, user_id)
        
        # Étape 2 : Pour chaque événement, ajoute le formatage
        for event in events:
            date_obj = event['date']
            
            # Gérer différents types de date
            if isinstance(date_obj, str):
                # Parser le string - peut contenir date seule ou date+heure
                try:
                    # Essayer de parser comme datetime ISO (gère les deux cas)
                    date_obj = datetime.fromisoformat(date_obj)
                    if hasattr(date_obj, 'date'):
                        date_obj = date_obj.date()
                except:
                    # Fallback : parser juste la date
                    date_obj = datetime.strptime(date_obj[:10], '%Y-%m-%d').date()
            elif hasattr(date_obj, 'date'):
                # Si c'est un datetime, extraire juste la date
                date_obj = date_obj.date()
            # Si c'est déjà un objet date, on ne fait rien
            
            # Ajoute les versions formatées
            event['month'] = date_obj.strftime('%b')
            event['day'] = date_obj.strftime('%d')
            event['weekday'] = date_obj.strftime('%a')
        
        # Étape 3 : Retourne la liste
        return events



    def get_waitlist_users(self, db: Session, event_id: int):
        """Récupère la liste des utilisateurs en waitlist avec leur position"""
        
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

