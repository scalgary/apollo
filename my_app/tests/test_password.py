# tests/test_password.py
from db_models import User, PasswordReset
from utils import get_password_hash
from datetime import datetime, timedelta
import secrets

def test_forgot_password_success(client, create_user, test_user_email, test_password, db):
    """Test génération token reset"""
    user = create_user(email=test_user_email, password=test_password)

    
    # Demander reset
    response = client.post("/forgot-password", data={"email": test_user_email}, follow_redirects=False)
    
    assert response.status_code == 302
    
    # Vérifier token en DB
    reset = db.query(PasswordReset).first()
    assert reset is not None
    assert reset.token is not None

def test_forgot_password_email_not_exists(client):
    """Test reset avec email inexistant"""
    response = client.post("/forgot-password", data={"email": "notexist@example.com"}, follow_redirects=False)
    
    # Ne révèle pas si email existe (sécurité)
    assert response.status_code == 302

def test_reset_password_success(client, create_user, test_user_email, test_password, db):
    """Test reset password avec token valide"""
    # Créer user
    user = create_user(email=test_user_email, password=test_password)

    
    # Générer token
    client.post("/forgot-password", data={"email": test_user_email})
    reset = db.query(PasswordReset).first()
    
    # Reset password
    new_password = "newpassword123"
    response = client.post("/reset-password", data={
        "token": reset.token,
        "new_password": new_password
    }, follow_redirects=False)
    
    assert response.status_code == 302
    
    # Vérifier login avec nouveau password
    response = client.post("/login", data={
        "email": test_user_email,
        "password": new_password
    }, follow_redirects=False)
    assert response.status_code == 302

def test_reset_password_expired_token(client, create_user, test_user_email, test_password, db):
    """Test reset avec token expiré"""
    # Créer user
    user = create_user(email=test_user_email, password=test_password)

    
    # Créer token expiré (datetime NAIVE pour SQLite)
    expired_token = secrets.token_urlsafe(32)
    reset = PasswordReset(
        user_id=user.id,
        token=expired_token,
        expires_at=datetime.utcnow() - timedelta(hours=1)  # ← NAIVE datetime
    )
    db.add(reset)
    db.commit()
    
    # Essayer reset
    response = client.post("/reset-password", data={
        "token": expired_token,
        "new_password": "newpass"
    }, follow_redirects=False)
    
    assert response.status_code == 302
    assert "error" in response.headers["location"]