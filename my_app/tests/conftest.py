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
    """Créer une whitelist de test"""
    whitelist_file = tmp_path / "whitelist.csv"
    whitelist_file.write_text("email\ntest@example.com\nuser2@example.com\n")
    
    # Mock les paths CSV
    from utils import csv_loader
    monkeypatch.setattr(csv_loader, "WHITELIST_PATH", str(whitelist_file))
    
    # Créer aussi un fichier events vide
    events_file = tmp_path / "events.csv"
    events_file.write_text("date,max_spots\n2025-12-25,20\n")
    monkeypatch.setattr(csv_loader, "EVENTS_PATH", str(events_file))