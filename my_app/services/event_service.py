from sqlalchemy.orm import Session
from datetime import datetime, date
from db_models import User, Event, Attendee, EventType, UserEventTypeMembership
from utils import load_events, load_event_types


class EventService:
    """Service pour gérer les événements"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def import_event_types_from_csv(self):
        """Import event types from CSV (doit être appelé AVANT import_events)"""
        event_types_data = load_event_types()
        imported_count = 0
        
        for et_data in event_types_data:
            try:
                # Vérifier si existe déjà
                existing = self.db.query(EventType).filter(
                    EventType.event_type_name == et_data['event_type_name']
                ).first()
                
                if not existing:
                    event_type = EventType(
                        event_type_name=et_data['event_type_name'],
                        display_name=et_data['display_name'],
                        default_location=et_data['default_location'],
                        default_time_start=et_data['default_time_start'],
                        default_time_end=et_data['default_time_end'],
                        default_max_capacity=et_data['default_max_capacity'],
                        color=et_data['color']
                    )
                    self.db.add(event_type)
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
        
        self.db.commit()
        return imported_count

    def import_events_from_csv(self):
        """Import events from CSV into database"""
        events_data = load_events()
        imported_count = 0
        
        # Mapper event_type_name vers event_type_id
        event_types = {et.event_type_name: et.id for et in self.db.query(EventType).all()}
    
        for event_data in events_data:
            try:
                event_type_name = event_data['event_type_name']
                
                if event_type_name not in event_types:
                    print(f"Event type '{event_type_name}' not found, skipping")
                    continue
                
                event_date = datetime.strptime(event_data['date'], '%Y-%m-%d').date()
                
                # Check if event already exists
                existing = self.db.query(Event).filter(Event.date == event_date).first()
                
                if not existing:
                    event = Event(
                        event_type_id=event_types[event_type_name],
                        date=event_date,
                        confirmed_count=0
                    )
                    self.db.add(event)
                    imported_count += 1
                
            except Exception as e:
                print(f"Error importing event {event_data}: {e}")
                continue
    
        self.db.commit()
        return imported_count

    def get_all_events_with_user_status(self, user_id: int):
        """Récupère tous les événements avec le statut de l'utilisateur"""
        today = date.today()
        
        # Joindre Event avec EventType pour avoir default_max_capacity
        events = self.db.query(Event, EventType).join(
            EventType, Event.event_type_id == EventType.id
        ).filter(Event.date >= today).order_by(Event.date).all()
        
        result = []
    
        for event, event_type in events:
            # Chercher si l'utilisateur est inscrit
            attendee = self.db.query(Attendee).filter(
                Attendee.event_id == event.id,
                Attendee.user_id == user_id
            ).first()
        
            # Compter les personnes en waitlist
            waitlist_count = self.db.query(Attendee).filter(
                Attendee.event_id == event.id,
                Attendee.status == 'waiting'
            ).count()
            
            max_capacity = event_type.default_max_capacity
        
            # Construire le résultat
            result.append({
            'id': event.id,
            'date': event.date,
            'event_type_id': event_type.id,  # ← AJOUTER CETTE LIGNE
            'event_type_name': event_type.event_type_name,
            'event_type_display': event_type.display_name,
            'max_spots': max_capacity,
            'confirmed_count': event.confirmed_count,
            'available_spots': max_capacity - event.confirmed_count,
            'waitlist_count': waitlist_count,
            'user_status': attendee.status if attendee else None
        })

        return result
    
    def get_events_for_schedule(self, user_id: int):
        """Récupère les événements formatés pour la page schedule"""
        
        # Récupère les événements
        events = self.get_all_events_with_user_status(user_id)
        
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

    def get_waitlist_users(self, event_id: int):
        """Récupère la liste des utilisateurs en waitlist avec leur position"""
        
        waitlist = self.db.query(Attendee, User).join(
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


    def get_user_memberships_formatted(self, user_id: int):
        """
        Récupère les memberships de l'utilisateur formatés pour le template.
        
        Retourne un dict avec event_1, event_2, etc. contenant toutes les infos
        nécessaires pour afficher les badges et filtrer les événements.
        
        Args:
            db: Session SQLAlchemy
            user_id: ID de l'utilisateur
        
        Returns:
            dict: {
                'event_1': {
                    'id': 1,
                    'event_type_name': 'open_play',
                    'display_name': 'JCC Sunday',
                    'location': 'Calgary Indoor Sports Arena',
                    'time_start': '19:00',
                    'time_end': '21:00',
                    'type': 'full_member',  # ou 'punch_card' ou 'none'
                    'remaining_credits': None  # None si full_member, sinon int
                },
                'event_2': {...}
            }
        """
        # 1. Récupérer tous les EventTypes par ordre d'ID
        event_types = self.db.query(EventType).order_by(EventType.id).all()
        
        result = {}
        
        # 2. Pour chaque EventType, créer une entrée event_1, event_2, etc.
        for index, event_type in enumerate(event_types, start=1):
            
            # 3. Récupérer le membership de l'utilisateur pour ce type
            membership = self.db.query(UserEventTypeMembership).filter(
                UserEventTypeMembership.user_id == user_id,
                UserEventTypeMembership.event_type_id == event_type.id
            ).first()
            
            # 4. Déterminer type et crédits
            if membership:
                membership_type = membership.membership_type
                remaining_credits = membership.remaining_credits
            else:
                # DÉFAUT: punch_card avec 0 crédits (pas d'accès)
                membership_type = 'punch_card'
                remaining_credits = 0
            
            # 5. Construire l'objet pour le template
            result[f'event_{index}'] = {
                'id': event_type.id,
                'event_type_name': event_type.event_type_name,
                'display_name': event_type.display_name,
                'location': event_type.default_location,
                'time_start': event_type.default_time_start,
                'time_end': event_type.default_time_end,
                'type': membership_type,
                'remaining_credits': remaining_credits
            }
        
        return result
    
    def get_event_details(self, event_id: int, user_id: int):
        """
        Récupère les détails complets d'un événement pour la page /event/{id}
        
        Returns:
            dict: {
                'event': {...},
                'event_type': {...},
                'user_membership': {...},
                'user_status': str,
                'confirmed_participants': [...],
                'waitlist': [...]
            }
        """
        from datetime import date
        
        # 1. Récupérer l'événement avec son type
        event_query = self.db.query(Event, EventType).join(
            EventType, Event.event_type_id == EventType.id
        ).filter(Event.id == event_id).first()
        
        if not event_query:
            return None
        
        event, event_type = event_query
        
        # 2. Récupérer le membership du user pour ce type d'événement
        membership = self.db.query(UserEventTypeMembership).filter(
            UserEventTypeMembership.user_id == user_id,
            UserEventTypeMembership.event_type_id == event_type.id
        ).first()
        
        # 3. Récupérer le statut du user pour cet événement
        attendee = self.db.query(Attendee).filter(
            Attendee.event_id == event_id,
            Attendee.user_id == user_id
        ).first()
        
        user_status = attendee.status if attendee else None
        
        # 4. Récupérer la liste des participants confirmés (ordre d'inscription)
        confirmed = self.db.query(Attendee, User).join(
            User, Attendee.user_id == User.id
        ).filter(
            Attendee.event_id == event_id,
            Attendee.status == 'confirmed'
        ).order_by(Attendee.registered_at).all()
        
        confirmed_participants = [
            {'display_name': user.display_name}
            for attendee, user in confirmed
        ]
        
        # 5. Récupérer la waitlist (ordre d'inscription)
        waitlist_query = self.db.query(Attendee, User).join(
            User, Attendee.user_id == User.id
        ).filter(
            Attendee.event_id == event_id,
            Attendee.status == 'waitlist'  # ← Corrigé de 'waiting' à 'waitlist'
        ).order_by(Attendee.registered_at).all()

        waitlist = []
        user_waitlist_position = None

        for idx, (attendee, user) in enumerate(waitlist_query, start=1):
            waitlist.append({
                'position': idx,
                'display_name': user.display_name
            })
            # Si c'est le user actuel, sauvegarder sa position
            if attendee.user_id == user_id:
                user_waitlist_position = idx

        
        # 6. Calculer les jours avant l'événement
        today = date.today()
        event_date = event.date
        if hasattr(event_date, 'date'):
            event_date = event_date.date()
        days_until_event = (event_date - today).days
        
        # 7. Formater la date
        event_date_formatted = {
            'month': event_date.strftime('%B'),
            'day': event_date.strftime('%d'),
            'year': event_date.strftime('%Y'),
            'weekday': event_date.strftime('%A')
        }
        
        return {
            'event': {
                'id': event.id,
                'date': event.date,
                'date_formatted': event_date_formatted,
                'confirmed_count': event.confirmed_count,
                'max_capacity': event_type.default_max_capacity,
                'available_spots': event_type.default_max_capacity - event.confirmed_count,
                'days_until': days_until_event
            },
            'event_type': {
                'id': event_type.id,
                'event_type_name': event_type.event_type_name,
                'display_name': event_type.display_name,
                'location': event_type.default_location,
                'time_start': event_type.default_time_start,
                'time_end': event_type.default_time_end
            },
            'user_membership': {
                'type': membership.membership_type if membership else 'punch_card',
                'remaining_credits': membership.remaining_credits if membership else 0
            },
            'user_status': user_status,
            'user_waitlist_position': user_waitlist_position,  # ← AJOUTER

            'confirmed_participants': confirmed_participants,
            'waitlist': waitlist
        }