from sqlalchemy.orm import Session
from datetime import datetime, date
from db_models import User, Event, Attendee, EventType, UserEventTypeMembership
from utils import load_events, load_event_types

from datetime import datetime, timedelta, timezone



class RegistrationService:
    def __init__(self, db: Session):
        self.db = db
    def get_event_with_type(self, event_id: int):
        #A. Vérifier que l'Event existe
        event_obj = self.db.query(Event).filter(Event.id == event_id).first()
        if not event_obj:
            raise ValueError("Event not found")
    
        # B. Récupérer l'EventType (doit toujours exister)
        event_type_obj = self.db.query(EventType).filter(
            EventType.id == event_obj.event_type_id
            ).first()
    
        if not event_type_obj:
            # Ça ne devrait JAMAIS arriver (integrity constraint)
            raise Exception("Database integrity error: Event has invalid event_type_id")
        
        return event_obj, event_type_obj    # ← Indentation correcte
    
    def check_user_already_registered(self, event_id: int, user_id: int):
        # B. Vérifier user pas déjà inscrit
        attendee_obj = self.db.query(Attendee).filter(
            Attendee.event_id == event_id,
            Attendee.user_id == user_id
        ).first()
    
        return attendee_obj is not None  # ✅ Plus concis
    
    def get_UserEventTypeMembership(self, event_id, user_id):
        event_obj, event_type_obj = self.get_event_with_type(event_id)

        membership_obj = self.db.query(UserEventTypeMembership).filter(
        UserEventTypeMembership.event_type_id == event_type_obj.id,
        UserEventTypeMembership.user_id == user_id
        ).first()

        return membership_obj  # Peut être None
    
    def get_days_until_event(self, event_id : int):
        today = date.today()
        event_obj, event_type_obj = self.get_event_with_type(event_id)
        event_date = event_obj.date

    # Normaliser la date (au cas où)
        if isinstance(event_date, str):
            event_date = date.fromisoformat(event_date)
        elif hasattr(event_date, 'date'):
            event_date = event_date.date()
    
        days_until_event = (event_date - today).days
        return days_until_event
    
    def get_remaining_credits(self,user_id, event_id):
        membership_obj = self.get_UserEventTypeMembership(event_id, user_id)
        if not membership_obj:
            return 0
        membership_type = membership_obj.membership_type
        remaining_credits = membership_obj.remaining_credits
        if membership_type=="punch_card":
            return remaining_credits
        else:
            return None
        
    def is_event_full(self,event_id):
            going_count = self.db.query(Attendee).filter(
            Attendee.event_id == event_id,
            Attendee.status == "going"
            ).count()
            event_obj, event_type_obj = self.get_event_with_type(event_id)
            max_capacity = event_type_obj.default_max_capacity
            return going_count >= max_capacity
 

    def register_user(self, user_id: int, event_id: int) -> dict:
        # Retourne {"success": True, "status": "going"/"waitlist"}
        # Ou lève une exception si erreur
        # is already refisterd?
        # A. MANQUE cette vérification au début!
        if self.check_user_already_registered(event_id, user_id):
            raise ValueError("Already registered")
        membership_obj = self.get_UserEventTypeMembership(event_id, user_id)
        if not membership_obj:
            raise ValueError("No membership for this event type")
        # C. Vérifier règle 7 jours pour punch_card
        days_until = self.get_days_until_event(event_id)
        if membership_obj.membership_type == "punch_card" and days_until > 7:
            raise ValueError("Event not yet available for punch card users")

        # D. Vérifier crédits pour punch_card
        if membership_obj.membership_type == "punch_card":
            remaining_credits = self.get_remaining_credits(user_id, event_id)
            if remaining_credits is None or remaining_credits <= 0:
                raise ValueError("No credits remaining")
    

        is_full = self.is_event_full(event_id)
        if is_full:
            status = 'waitlist'
            credit_used = 0
        else:
            status = 'going'
            credit_used = 1 if membership_obj.membership_type == 'punch_card' else 0
            # F. Créer Attendee
        attendee = Attendee(
            event_id=event_id,
            user_id=user_id,
            status=status,
            credit_used=credit_used,
            registered_at=datetime.now(timezone.utc)
        )
        # G. Décrémenter crédits si going + punch_card
        if status == 'going' and membership_obj.membership_type == 'punch_card':
            membership_obj.remaining_credits -= 1

        self.db.add(attendee)
        self.db.commit()

        return {"success": True, "status": status}
    
    def unregister_user(self, user_id: int, event_id: int):
        #       A. Vérifier Attendee existe
        attendee_obj = self.db.query(Attendee).filter(
            Attendee.event_id == event_id,
            Attendee.user_id == user_id
        ).first()
        if not attendee_obj or attendee_obj.status not in ("going","waitlist"):
            raise ValueError("No registration for this event")
        #B. Calculer deadline (date + time_start - 4h)
        event_obj, event_type_obj = self.get_event_with_type(event_id)
        event_date = event_obj.date
        event_start = event_type_obj.default_time_start
        # Normaliser la date si nécessaire
        if isinstance(event_date, str):
            event_date = date.fromisoformat(event_date)
        elif hasattr(event_date, 'date'):
            event_date = event_date.date()
         #Combiner date + heure pour avoir un datetime complet
        event_datetime = datetime.combine(
            event_date, 
            datetime.strptime(event_start, "%H:%M").time()
        )

        # Calculer la deadline (4h avant)
        deadline = event_datetime - timedelta(hours=4)

        # Vérifier si on est avant la deadline
        now = datetime.now()
        if now >= deadline:
            raise ValueError("Too late to cancel - deadline passed")
        #E. Si status='going' ET credit_used=1 → restaurer crédit (membership.remaining_credits += 1)
        # D. Restaurer le crédit si nécessaire
        if attendee_obj.status == "going" and attendee_obj.credit_used == 1:
        # Récupérer le membership
            membership_obj = self.get_UserEventTypeMembership(event_id, user_id)
    
            if membership_obj and membership_obj.membership_type == "punch_card":
        # Restaurer le crédit
                membership_obj.remaining_credits += 1
        #F. Supprimer l'Attendee (db.delete)
        was_going = attendee_obj.status == "going"
        self.db.delete(attendee_obj)

        if was_going:
            self.promote_from_waitlist(event_id)
        
        self.db.commit()

    def promote_from_waitlist(self, event_id):
        #Trouver le premier en waitlist
        first_waitlist = self.db.query(Attendee).filter(
            Attendee.event_id == event_id,
            Attendee.status == 'waitlist'
        ).order_by(Attendee.registered_at.asc()).first()  # ← Premier inscrit
        
        if not first_waitlist:
            return  # Pas de waitlist, rien à faire
        first_waitlist.status = 'going'
        # 3. Récupérer membership pour gérer les crédits
        membership = self.get_UserEventTypeMembership(event_id, first_waitlist.user_id)
            # 4. Gérer credit_used selon le type
        if membership and membership.membership_type == 'punch_card':
            first_waitlist.credit_used = 1
            membership.remaining_credits -= 1
        else:
            # Full member
            first_waitlist.credit_used = 0



        




            
            









        






