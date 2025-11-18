import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, get_db
from main import app
import os

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"

@pytest.fixture(scope="function")
def db():
    """Crée une DB propre pour chaque test"""
    engine = create_engine(
        SQLALCHEMY_TEST_DATABASE_URL, 
        connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
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
    # ← FIX: Pas de context manager
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def test_user_email():
    return "test@example.com"

@pytest.fixture
def test_password():
    return "password123"

@pytest.fixture(autouse=True)
def setup_test_whitelist(tmp_path, monkeypatch):
    """Créer une whitelist de test avec le bon format"""
    
    # Créer le CSV whitelist avec les colonnes correctes
    whitelist_file = tmp_path / "whitelist.csv"
    whitelist_file.write_text(
        "email,membership_type,credits\n"
        "test@example.com,full_member,\n"
        "user2@example.com,punch_card,10\n"
        "fullmember@test.com,full_member,\n"
        "punchcard@test.com,punch_card,10\n"
    )
    
    # Mock le path de la whitelist
    from utils import csv_loader
    monkeypatch.setattr(csv_loader, "WHITELIST_PATH", str(whitelist_file))
    
    # Créer aussi un fichier events vide
    events_file = tmp_path / "events.csv"
    events_file.write_text("date,max_spots\n2025-12-25,20\n")
    monkeypatch.setattr(csv_loader, "EVENTS_PATH", str(events_file))


# ============================================
# FIXTURES DE DONNÉES (tes nouveaux fixtures)
# ============================================

@pytest.fixture
def full_member_user(db):
    """Fixture: créer un full member"""
    from db_models import User
        # ARRANGE - Préparer les données
    email = "fullmember@test.com"
    password_hash = "fake_hash_for_now"
    
    # ACT - Créer le user
    user = User(
        email=email,
        hashed_password=password_hash,
        membership_type='full_member',
        initial_credits=None,
        remaining_credits=None
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

    # À toi d'écrire!
    # Créer un User full_member
    # db.add(), db.commit(), db.refresh()
    # return user

@pytest.fixture
def punch_card_user(db):
    """Fixture: créer un punch card user avec 3 crédits"""
    from db_models import User
    email = "punchcard@test.com"
    password_hash = "fake_hash_for_now"
    user = User(
        email=email,
        hashed_password=password_hash,
        membership_type='punch_card',
        initial_credits=10,      # Capacité totale
        remaining_credits=3     # Ce qui reste (au début = total)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_event(db):
    """Fixture: créer un event de test"""
    from db_models import Event
    from datetime import datetime, timedelta
    
    event = Event(
        date=datetime.now() + timedelta(days=7),  # Event dans 7 jours
        max_spots=20
        # Autres champs nécessaires
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event

    # À toi!
    # date future
    # max_spots=20

def test_fixtures_work(db, full_member_user, punch_card_user, test_event):
    """Test rapide pour vérifier que les fixtures fonctionnent"""
    
    assert full_member_user.id is not None
    assert punch_card_user.remaining_credits == 3
    assert test_event.max_spots == 20
    
    print("✓ Tous les fixtures fonctionnent!")

@pytest.fixture
def mock_auth_punch_card(monkeypatch, punch_card_user):
    """
    Fixture: Simule que punch_card_user est connecté
    """
    def fake_get_user(request, db):
        return punch_card_user
    
    from routes import events
    monkeypatch.setattr(events, "get_user_from_cookie", fake_get_user)

