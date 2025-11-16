
from fastapi import APIRouter, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from models import User, PasswordReset
from auth import get_password_hash, authenticate_user, create_access_token
from allowed_emails import ALLOWED_EMAILS
from datetime import datetime, timedelta
import logging
import secrets

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/login")
def login(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    """Authentifier un utilisateur"""
    user = authenticate_user(db, email, password)
    
    if not user:
        return RedirectResponse(url="/login?error=Invalid credentials", status_code=302)
    
    access_token = create_access_token(data={"sub": user.id})
    
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key="access_token", 
        value=access_token, 
        httponly=True,
        max_age=86400,
        samesite="lax",
        path="/"
    )
    logger.info(f"User {email} logged in")
    return response

@router.post("/signup")
def signup(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    """Créer un nouveau compte utilisateur (avec whitelist)"""
    # Vérifier si l'email est autorisé
    if email not in ALLOWED_EMAILS:
        return RedirectResponse(url="/signup?error=Email not authorized. Contact admin.", status_code=302)
    
    # Vérifier si l'utilisateur existe déjà
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return RedirectResponse(url="/signup?error=Email already exists", status_code=302)
    
    hashed_password = get_password_hash(password)
    user = User(email=email, hashed_password=hashed_password)
    db.add(user)
    db.commit()
    
    logger.info(f"New user created: {email}")
    return RedirectResponse(url="/login?success=Account created", status_code=302)

@router.get("/logout")
def logout():
    """Déconnecter l'utilisateur"""
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(key="access_token")
    return response

@router.post("/forgot-password")
def forgot_password(email: str = Form(...), db: Session = Depends(get_db)):
    """Générer un token de reset de mot de passe"""
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        # Ne pas révéler si l'email existe ou non (sécurité)
        return RedirectResponse(url="/forgot-password?success=If email exists, reset link sent", status_code=302)
    
    # Générer un token unique
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=1)  # Expire dans 1h
    
    # Supprimer les anciens tokens de cet utilisateur
    db.query(PasswordReset).filter(PasswordReset.user_id == user.id).delete()
    
    # Créer le nouveau token
    reset = PasswordReset(user_id=user.id, token=token, expires_at=expires_at)
    db.add(reset)
    db.commit()
    
    logger.info(f"Password reset token generated for {email}")
    
    # Pour l'instant, afficher le lien (en prod, envoyer par email)
    reset_link = f"http://localhost:8000/reset-password?token={token}"
    return RedirectResponse(url=f"/forgot-password?success=Reset link: {reset_link}", status_code=302)

@router.post("/reset-password")
def reset_password(
    token: str = Form(...), 
    new_password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Réinitialiser le mot de passe avec un token"""
    # Trouver le token
    reset = db.query(PasswordReset).filter(PasswordReset.token == token).first()
    
    if not reset:
        return RedirectResponse(url="/reset-password?error=Invalid token", status_code=302)
    
    # Vérifier expiration
    if reset.expires_at < datetime.utcnow():
        db.delete(reset)
        db.commit()
        return RedirectResponse(url="/reset-password?error=Token expired", status_code=302)
    
    # Mettre à jour le mot de passe
    user = db.query(User).filter(User.id == reset.user_id).first()
    user.hashed_password = get_password_hash(new_password)
    
    # Supprimer le token
    db.delete(reset)
    db.commit()
    
    logger.info(f"Password reset successful for user {user.email}")
    return RedirectResponse(url="/login?success=Password reset successful", status_code=302)
