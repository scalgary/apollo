# tests/test_helpers.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from database import Base

def create_test_session():
    """Crée une session de test SQLite en mémoire"""
    SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"
    
    engine = create_engine(
        SQLALCHEMY_TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    
    return session


def create_user_helper(db_session):
    """Factory pour créer des users"""
    def _create(email="test@apollo.com", display_name="Test", real_name="Test Real", password="password123"):
        from db_models import User
        from utils import get_password_hash  # ← Utilise ta fonction existante
        
        hashed_password = get_password_hash(password)  # ← Au lieu de CryptContext
        
        user = User(
            email=email,
            display_name=display_name,
            real_name=real_name,
            hashed_password=hashed_password
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    
    return _create





def create_event_type_helper(db_session):
    """Factory pour créer des event types"""
    def _create(name="open_play", display_name="Intérieur", default_max_capacity=20, 
                default_location="Cedarbrae", color="#4A90E2"):
        from db_models import EventType
        
        event_type = EventType(
            name=name,
            display_name=display_name,
            default_location=default_location,
            default_time_start="19:00",
            default_time_end="21:00",
            default_max_capacity=default_max_capacity,
            color=color
        )
        db_session.add(event_type)
        db_session.commit()
        db_session.refresh(event_type)
        return event_type
    
    return _create


def create_event_helper(db_session):
    """Factory pour créer des events"""
    def _create(event_type_id, event_date=None, confirmed_count=0):
        from db_models import Event
        from datetime import date, timedelta
        
        if event_date is None:
            event_date = date.today() + timedelta(days=14)
        
        event = Event(
            event_type_id=event_type_id,
            date=event_date,
            confirmed_count=confirmed_count
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)
        return event
    
    return _create


def create_membership_helper(db_session):
    """Factory pour créer des memberships"""
    def _create(user_id, event_type_id, membership_type="full_member",
                total_credits_purchased=None, remaining_credits=None):
        from db_models import UserEventTypeMembership
        
        membership = UserEventTypeMembership(
            user_id=user_id,
            event_type_id=event_type_id,
            membership_type=membership_type,
            total_credits_purchased=total_credits_purchased,
            remaining_credits=remaining_credits
        )
        db_session.add(membership)
        db_session.commit()
        db_session.refresh(membership)
        return membership
    
    return _create


def create_attendee_helper(db_session):
    """Factory pour créer des attendees"""
    def _create(user_id, event_id, status="going", credit_used=0):
        from db_models import Attendee
        
        attendee = Attendee(
            user_id=user_id,
            event_id=event_id,
            status=status,
            credit_used=credit_used
        )
        db_session.add(attendee)
        db_session.commit()
        db_session.refresh(attendee)
        return attendee
    
    return _create