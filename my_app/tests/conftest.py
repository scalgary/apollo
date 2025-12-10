import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import sys
from pathlib import Path

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"
sys.path.insert(0, str(Path(__file__).parent.parent))
from database import Base, get_db
from main import app

# ============================================
# FIXTURES DE BASE
# ============================================

@pytest.fixture(scope="function")
def db():
    """Crée une DB propre pour chaque test avec les 2 event_types"""
    engine = create_engine(
        SQLALCHEMY_TEST_DATABASE_URL, 
        connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    

    # IMPORTANT: Créer les 2 event_types dans chaque DB de test
    from db_models import EventType
    open_play = EventType(
        event_type_name='open_play',
        display_name='Intérieur',
        default_location='Calgary Indoor Sports Arena',
        default_time_start='19:00',
        default_time_end='21:00',
        default_max_capacity=20,
        color='#4A90E2'
    )
    competitive = EventType(
        event_type_name='competitive',
        display_name='Extérieur',
        default_location='Riley Park Outdoor Courts',
        default_time_start='14:00',
        default_time_end='16:00',
        default_max_capacity=16,
        color='#7ED321'
    )
        # Créer toutes les tables
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    
    db.add(open_play)
    db.add(competitive)
    db.commit()
    
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        if os.path.exists("test.db"):
            os.remove("test.db")

@pytest.fixture(scope="function")
def client(db):
    """Client de test avec DB"""
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def test_user_email():
    return "user1@example.com"

@pytest.fixture
def test_password():
    return "password123"

# ============================================
# FIXTURES DE DONNÉES
# ============================================

@pytest.fixture
def full_member_user(db):
    """Fixture: créer un full member pour open_play"""
    from db_models import User, UserEventTypeMembership
    from utils import get_password_hash
    
    password = "testpass123"
    
    user = User(
        email="fullmember@test.com",
        hashed_password=get_password_hash(password),
        real_name="Test Full",
        display_name="Full Test"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    membership1 = UserEventTypeMembership(
        user_id=user.id,
        event_type_id=1,
        membership_type='full_member',
        total_credits_purchased=None,
        remaining_credits=None  # ← AJOUTÉ (None = illimité pour full_member)
    )
    db.add(membership1)
    db.commit()
    
    user.plain_password = password
    return user

@pytest.fixture
def punch_card_user(db):
    """Fixture: créer un punch card user avec 10 crédits"""
    from db_models import User, UserEventTypeMembership
    from utils import get_password_hash

    password = "testpass123"
    
    user = User(
        email="punchcard@test.com",
        hashed_password=get_password_hash(password),
        real_name="Test Punch",
        display_name="Punch Test"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    membership = UserEventTypeMembership(
        user_id=user.id,
        event_type_id=1,
        membership_type='punch_card',
        total_credits_purchased=10,
        remaining_credits=10  # ← AJOUTÉ (au début = total)
    )
    db.add(membership)
    db.commit()
    
    user.plain_password = password
    return user


# ============================================
# FIXTURES POUR EVENTS
# ============================================

@pytest.fixture
def test_event(db):
    """Fixture: créer un event de test (open_play, dans 7 jours)"""
    from db_models import Event
    from datetime import datetime, timedelta
    
    event = Event(
        event_type_id=1,  # open_play
        date=(datetime.now().date() + timedelta(days=7)),
        confirmed_count=0
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@pytest.fixture
def create_event(db):
    """Factory pour créer des events"""
    from db_models import Event
    from datetime import datetime, timedelta
    
    def _create_event(event_type_id=1, days_from_now=7, confirmed_count=0):
        event = Event(
            event_type_id=event_type_id,
            date=(datetime.now().date() + timedelta(days=days_from_now)),
            confirmed_count=confirmed_count
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event
    
    return _create_event


@pytest.fixture
def create_attendee(db):
    """Factory pour créer des attendees"""
    from db_models import Attendee
    from datetime import datetime, timezone
    
    def _create_attendee(event, user, status='confirmed'):
        attendee = Attendee(
            event_id=event.id,
            user_id=user.id,
            status=status,
            registered_at=datetime.now(timezone.utc)
        )
        db.add(attendee)
        db.commit()
        db.refresh(attendee)
        return attendee
    
    return _create_attendee

@pytest.fixture
def create_user(db):
    """Factory pour créer des users avec memberships"""
    from db_models import User, UserEventTypeMembership
    from utils import get_password_hash
    
    def _create_user(
        email="test@example.com",
        password="testpass123",
        real_name="Test User",
        display_name="Test User",
        event_type_id=1,
        membership_type="full_member",
        total_credits=None
    ):
        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            real_name=real_name,
            display_name=display_name
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Calculer remaining_credits
        if membership_type == 'full_member':
            remaining = None  # Illimité
        else:
            remaining = total_credits if total_credits else 0
        
        membership = UserEventTypeMembership(
            user_id=user.id,
            event_type_id=event_type_id,
            membership_type=membership_type,
            total_credits_purchased=total_credits,
            remaining_credits=remaining  # ← AJOUTÉ
        )
        db.add(membership)
        db.commit()
        
        user.plain_password = password
        return user
    
    return _create_user
# # ============================================
# # TEST DES FIXTURES
# # ============================================

# def test_fixtures_work(db, full_member_user, punch_card_user, test_event):
#     """Test rapide pour vérifier que les fixtures fonctionnent"""
#     from db_models import UserEventTypeMembership, EventType
    
#     # Vérifier event_types
#     event_types = db.query(EventType).all()
#     assert len(event_types) == 2
    
#     # Vérifier full_member_user
#     full_membership = db.query(UserEventTypeMembership).filter_by(
#         user_id=full_member_user.id,
#         event_type_id=1
#     ).first()
#     assert full_membership.membership_type == 'full_member'
#     assert full_membership.remaining_credits is None  # ← MODIFIÉ
    
#     # Vérifier punch_card_user
#     punch_membership = db.query(UserEventTypeMembership).filter_by(
#         user_id=punch_card_user.id,
#         event_type_id=1
#     ).first()
#     assert punch_membership.membership_type == 'punch_card'
#     assert punch_membership.total_credits_purchased == 10
#     assert punch_membership.remaining_credits == 10  # ← AJOUTÉ
    
#     assert test_event.event_type_id == 1
    
#     print("✓ Tous les fixtures fonctionnent!")

# @pytest.fixture
# def mock_auth_punch_card(monkeypatch, punch_card_user):
#     """Fixture: Simule que punch_card_user est connecté"""
#     def fake_get_user(request, db):
#         return punch_card_user
    
#     from routes import events
#     monkeypatch.setattr(events, "get_user_from_cookie", fake_get_user)

# @pytest.fixture(autouse=True)
# def setup_test_whitelist(tmp_path, monkeypatch):
    # """Créer une whitelist de test avec le nouveau format"""
    # whitelist_file = tmp_path / "whitelist.csv"
    # whitelist_file.write_text(
    #     "email,real_name,event_type_name,membership_type,total_credits_purchased\n"
    #     "user1@example.com,Test User,open_play,full_member,\n"
    #     "user1@example.com,Test User,competitive,punch_card,5\n"
    # )
    
    # from utils import csv_loader
    # monkeypatch.setattr(csv_loader, "WHITELIST_PATH", str(whitelist_file))

