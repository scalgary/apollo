from sqlalchemy.orm import Session
from db_models import User, UserEventTypeMembership, EventType


class UserService:
    """Service pour gérer les utilisateurs et leurs memberships"""
    
    def get_user_memberships(self, db: Session, user_id: int):
        """
        Récupère les memberships de l'utilisateur pour tous les event types
        
        Returns:
            dict: {
                'event_1': {
                    'name': 'competitive',
                    'type': 'full_member',
                    'remaining_credits': None,
                    'total_credits_purchased': None,
                    'display_name': 'Extérieur',
                    'location': 'Riley Park Outdoor Courts',
                    'time_start': '14:00',
                    'time_end': '16:00',
                    'max_capacity': 16,
                    'color': '#7ED321'
                },
                'event_2': {...}
            }
        """
        # Récupérer tous les event types TRIÉS par nom
        event_types = db.query(EventType).order_by(EventType.name).all()
        
        # Récupérer les memberships de l'utilisateur
        memberships = db.query(UserEventTypeMembership).filter(
            UserEventTypeMembership.user_id == user_id
        ).all()
        
        # Créer un dict pour lookup rapide
        membership_dict = {m.event_type_id: m for m in memberships}
        
        result = {}
        for index, event_type in enumerate(event_types, start=1):
            membership = membership_dict.get(event_type.id)
            
            key = f"event_{index}"
            
            if membership:
                result[key] = {
                    'name': event_type.name,
                    'type': membership.membership_type,
                    'remaining_credits': membership.remaining_credits,
                    'total_credits_purchased': membership.total_credits_purchased,
                    'display_name': event_type.display_name,
                    'location': event_type.default_location,
                    'time_start': event_type.default_time_start,
                    'time_end': event_type.default_time_end,
                    'max_capacity': event_type.default_max_capacity,
                    'color': event_type.color
                }
            else:
                # Pas de membership = pas accès
                result[key] = {
                    'name': event_type.name,
                    'type': None,
                    'remaining_credits': None,
                    'total_credits_purchased': None,
                    'display_name': event_type.display_name,
                    'location': event_type.default_location,
                    'time_start': event_type.default_time_start,
                    'time_end': event_type.default_time_end,
                    'max_capacity': event_type.default_max_capacity,
                    'color': event_type.color
                }
        
        return result