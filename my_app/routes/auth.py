# my_app/routes/auth.py
from fastapi import APIRouter, Form, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from db_models import User, PasswordReset
from utils import get_password_hash, authenticate_user, create_access_token, load_whitelist
from datetime import datetime, timedelta, timezone
import logging
import secrets

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="templates")

# === SIGNUP ===
@router.post("/signup")
def signup(email: str = Form(...), 
           password: str = Form(...), 
           display_name: str = Form(""),  # NEW: optional (empty by default)
           db: Session = Depends(get_db)):
    """Créer un nouveau compte utilisateur (avec whitelist)"""
    whitelist = load_whitelist()
    
    # Vérifier si l'email est dans la whitelist (dict maintenant)
    if email not in whitelist:
        return RedirectResponse(url="/signup?error=Email not authorized. Contact admin.", status_code=302)
    
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return RedirectResponse(url="/signup?error=Email already exists", status_code=302)
    
    # Récupérer les infos de membership depuis la whitelist
    user_info = whitelist[email]

    hashed_password = get_password_hash(password)
    user = User(
        email=email, 
        hashed_password=hashed_password,
        real_name=user_info['real_name'],
        display_name=display_name,
        membership_type=user_info['membership_type'],
        initial_credits=user_info['initial_credits'],
        remaining_credits=user_info['initial_credits']  # Au début, remaining = initial
    )
    db.add(user)
    db.commit()
    
    logger.info(f"New user created: {email} ({user_info['membership_type']})")
    return RedirectResponse(url="/login?success=Account created", status_code=302)

# === LOGIN ===
@router.post("/login")
def login(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    """Authentifier un utilisateur"""
    
    # 1. Vérifier si email est dans la whitelist
    whitelist = load_whitelist()
    
    if email not in whitelist:
        # Email pas autorisé - message générique pour sécurité
        return RedirectResponse(
            url="/login?error=Invalid credentials", 
            status_code=302
        )
    
    # 2. Email dans whitelist - vérifier si compte existe
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        # Dans whitelist mais pas encore inscrit
        return RedirectResponse(
            url="/login?error=Please sign up first.", 
            status_code=302
        )

    # 3. Compte existe - vérifier password
    user = authenticate_user(db, email, password)#super important

    if not user:
        return RedirectResponse(url="/login?error=Invalid credentials", status_code=302)
    
    # 4. Tout est bon - login réussi
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

# === LOGOUT ===
@router.get("/logout")
def logout():
    """Déconnecter l'utilisateur"""
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(key="access_token")
    return response

# === FORGOT PASSWORD ===
@router.get("/forgot-password")
def forgot_password_page(request: Request):
    """Afficher le formulaire forgot password"""
    return templates.TemplateResponse("forgot-password.html", {"request": request})


# === RESET PASSWORD ===
@router.get("/reset-password")
def reset_password_page(request: Request, token: str):
    """Afficher le formulaire reset password"""
    return templates.TemplateResponse("reset-password.html", {
        "request": request,
        "token": token
    })


from datetime import datetime, timedelta  # ← Enlève timezone

@router.post("/forgot-password")
def forgot_password(email: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        return RedirectResponse(url="/forgot-password?success=If email exists, reset link sent", status_code=302)
    
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=1)  # ← Utilise utcnow() sans timezone
    
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

@router.post("/reset-password")
def reset_password(
    token: str = Form(...), 
    new_password: str = Form(...),
    db: Session = Depends(get_db)
):
    reset = db.query(PasswordReset).filter(PasswordReset.token == token).first()
    
    if not reset:
        return RedirectResponse(url="/login?error=Invalid token", status_code=302)
    
    if reset.expires_at < datetime.utcnow():  # ← Utilise utcnow() sans timezone
        db.delete(reset)
        db.commit()
        return RedirectResponse(url="/login?error=Token expired", status_code=302)
    
    user = db.query(User).filter(User.id == reset.user_id).first()
    user.hashed_password = get_password_hash(new_password)
    
    db.delete(reset)
    db.commit()
    
    logger.info(f"Password reset successful for user {user.email}")
    return RedirectResponse(url="/login?success=Password reset successful", status_code=302)