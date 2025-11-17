
from fastapi import APIRouter, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from db_models import User, PasswordReset
from utils import get_password_hash, authenticate_user, create_access_token
from datetime import datetime, timedelta
import logging
import secrets
from utils import load_whitelist  # ← Ajoute cet import

logger = logging.getLogger(__name__)
router = APIRouter()

# backend/routes/auth.py

@router.post("/signup")
def signup(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    """Créer un nouveau compte utilisateur (avec whitelist)"""
    
    # Vérifier si l'email est autorisé
    whitelist = load_whitelist()  # ← Change cette ligne
    if email not in whitelist:    # ← Change ALLOWED_EMAILS en whitelist
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


 

@router.get("/logout")
def logout():
    """Déconnecter l'utilisateur"""
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(key="access_token")
    return response


@router.post("/forgot-password")
def forgot_password(email: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        return RedirectResponse(url="/forgot-password?success=If email exists, reset link sent", status_code=302)
    
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)  # ← FIX ICI AUSSI
    
    db.query(PasswordReset).filter(PasswordReset.user_id == user.id).delete()
    
    reset = PasswordReset(user_id=user.id, token=token, expires_at=expires_at)
    db.add(reset)
    db.commit()
    
    reset_link = f"/reset-password?token={token}"
    
    print(f"\n🔗 PASSWORD RESET LINK: http://localhost:8000{reset_link}\n")
    logger.info(f"Password reset link: {reset_link}")
    
    return RedirectResponse(
        url=f"/forgot-password?success=Check your email&link={reset_link}", 
        status_code=302
    )
from datetime import datetime, timedelta, timezone  # ← Ajoute timezone

@router.post("/reset-password")
def reset_password(
    token: str = Form(...), 
    new_password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Réinitialiser le mot de passe avec un token"""
    reset = db.query(PasswordReset).filter(PasswordReset.token == token).first()
    
    if not reset:
        return RedirectResponse(url="/login?error=Invalid token", status_code=302)
    
    # ← FIX: Utilise datetime.now(timezone.utc) au lieu de utcnow()
    if reset.expires_at < datetime.now(timezone.utc):
        db.delete(reset)
        db.commit()
        return RedirectResponse(url="/login?error=Token expired", status_code=302)
    
    # Mettre à jour le mot de passe
    user = db.query(User).filter(User.id == reset.user_id).first()
    user.hashed_password = get_password_hash(new_password)
    
    # Supprimer le token
    db.delete(reset)
    db.commit()
    
    logger.info(f"Password reset successful for user {user.email}")
    return RedirectResponse(url="/login?success=Password reset successful", status_code=302)