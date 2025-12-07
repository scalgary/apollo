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
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Déterminer l'environnement (DEV ou PROD)
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'production')
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:8000')

# === SIGNUP ===

@router.post("/signup")
def signup(email: str = Form(...), 
           password: str = Form(...), 
           display_name: str = Form(""),
           db: Session = Depends(get_db)):
    """Créer un nouveau compte utilisateur avec memberships"""
    from db_models import EventType, UserEventTypeMembership
    
    whitelist = load_whitelist()
    
    # 1. Vérifier whitelist
    if email not in whitelist:
        return RedirectResponse(
            url="/signup?error=Email not authorized. Contact admin.", 
            status_code=302
        )
    
    # 2. Vérifier si existe déjà
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return RedirectResponse(
            url="/signup?error=Email already exists", 
            status_code=302
        )
    
    user_info = whitelist[email]
    
    # 3. Créer le User
    hashed_password = get_password_hash(password)
    user = User(
        email=email, 
        hashed_password=hashed_password,
        real_name=user_info['real_name'],
        display_name=display_name if display_name else user_info['real_name']
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # 4. Créer les memberships pour chaque event_type
    for membership_data in user_info['memberships']:
        # Trouver l'event_type_id depuis le nom
        event_type = db.query(EventType).filter(
            EventType.name == membership_data['event_type_name']
        ).first()
        
        if not event_type:
            logger.error(f"Event type not found: {membership_data['event_type_name']}")
            continue
        
        # Calculer remaining_credits
        if membership_data['membership_type'] == 'full_member':
            remaining = None
        else:
            remaining = membership_data['total_credits_purchased'] or 0
        
        # Créer le membership
        membership = UserEventTypeMembership(
            user_id=user.id,
            event_type_id=event_type.id,
            membership_type=membership_data['membership_type'],
            total_credits_purchased=membership_data['total_credits_purchased'],
            remaining_credits=remaining
        )
        db.add(membership)
    
    db.commit()
    
    logger.info(f"New user created: {email} with {len(user_info['memberships'])} memberships")
    return RedirectResponse(url="/login?success=Account created", status_code=302)
# === LOGIN ===
@router.post("/login")
def login(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    """Authentifier un utilisateur"""
    
    whitelist = load_whitelist()
    
    if email not in whitelist:
        return RedirectResponse(
            url="/login?error=Invalid credentials", 
            status_code=302
        )
    
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        return RedirectResponse(
            url="/login?error=Please sign up first.", 
            status_code=302
        )

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

# === LOGOUT ===
@router.get("/logout")
def logout():
    """Déconnecter l'utilisateur"""
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(key="access_token")
    return response

# === FORGOT PASSWORD - Étape 1: Demander email ===
@router.get("/forgot-password")
def forgot_password_page(request: Request):
    """Afficher formulaire pour entrer email"""
    return templates.TemplateResponse("forgot-password.html", {"request": request})

@router.post("/forgot-password")
def forgot_password(email: str = Form(...), db: Session = Depends(get_db)):
    """Générer token de reset et afficher le lien (dev) ou envoyer email (prod)"""
    
    user = db.query(User).filter(User.email == email).first()
    
    # Sécurité: Ne pas révéler si l'email existe ou pas
    if not user:
        logger.warning(f"Password reset attempt for non-existent email: {email}")
        return RedirectResponse(
            url="/forgot-password?success=If your email is registered, you will receive a reset link", 
            status_code=302
        )
    
    # Générer token sécurisé
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    
    # Supprimer anciens tokens pour cet user
    db.query(PasswordReset).filter(PasswordReset.user_id == user.id).delete()
    
    # Créer nouveau token
    reset = PasswordReset(user_id=user.id, token=token, expires_at=expires_at)
    db.add(reset)
    db.commit()
    
    # Construire le lien de reset avec BASE_URL
    reset_link = f"{BASE_URL}/reset-password?token={token}"
    
    # EN DÉVELOPPEMENT: Toujours afficher dans console
    if ENVIRONMENT == 'development':
        print(f"\n{'='*60}")
        print(f"🔗 PASSWORD RESET LINK FOR {email}")
        print(f"{'='*60}")
        print(f"{reset_link}")
        print(f"{'='*60}\n")
        logger.info(f"[DEV] Password reset token generated for {email}")
    
    # Essayer d'envoyer l'email si configuré
    email_sent = send_reset_email(email, reset_link)
    
    if email_sent:
        logger.info(f"Reset email sent to {email}")
    elif ENVIRONMENT == 'production':
        # En prod, si email ne part pas, c'est un problème
        logger.error(f"Failed to send reset email in production for {email}")
        return RedirectResponse(
            url="/forgot-password?error=Failed to send email. Please contact support.", 
            status_code=302
        )
    
    return RedirectResponse(
        url="/forgot-password?success=Check your email for reset instructions", 
        status_code=302
    )

# === RESET PASSWORD - Étape 2: Entrer nouveau password ===
@router.get("/reset-password")
def reset_password_page(request: Request, token: str):
    """Afficher formulaire pour entrer nouveau password"""
    return templates.TemplateResponse("reset-password.html", {
        "request": request,
        "token": token
    })

@router.post("/reset-password")
def reset_password(
    token: str = Form(...), 
    new_password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Changer le password avec le token"""
    
    # Vérifier que le token existe
    reset = db.query(PasswordReset).filter(PasswordReset.token == token).first()
    
    if not reset:
        logger.warning(f"Invalid token used: {token[:10]}...")
        return RedirectResponse(
            url="/login?error=Invalid or expired reset link", 
            status_code=302
        )
    
    # Vérifier que le token n'est pas expiré
    # Gérer compatibilité SQLite (retourne naive) et PostgreSQL (retourne aware)
    expires_at = reset.expires_at
    if expires_at.tzinfo is None:
        # SQLite retourne naive, on ajoute UTC
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if expires_at < datetime.now(timezone.utc):
        logger.warning(f"Expired token used for user {reset.user_id}")
        db.delete(reset)
        db.commit()
        return RedirectResponse(
            url="/login?error=Reset link expired. Please request a new one.", 
            status_code=302
        )
    
    # Token valide - changer le password
    user = db.query(User).filter(User.id == reset.user_id).first()
    user.hashed_password = get_password_hash(new_password)
    
    # Supprimer le token (usage unique)
    db.delete(reset)
    db.commit()
    
    logger.info(f"Password successfully reset for user {user.email}")
    return RedirectResponse(url="/login?success=Password reset successful! You can now login.", status_code=302)
# === FONCTION POUR ENVOI EMAIL ===
def send_reset_email(to_email: str, reset_link: str):
    """
    Envoyer email de reset password via SMTP
    
    Returns:
        bool: True si email envoyé, False sinon
    """
    email_from = os.environ.get('EMAIL_FROM')
    email_password = os.environ.get('EMAIL_PASSWORD')
    smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    
    # Si pas configuré, on log et on retourne False
    if not all([email_from, email_password]):
        if ENVIRONMENT == 'development':
            logger.info("📧 Email not configured - using console output only (dev mode)")
        else:
            logger.error("❌ Email configuration missing (EMAIL_FROM or EMAIL_PASSWORD)")
        return False
    
    # Email subject
    subject = "Apollo - Reset Your Password"
    
    # Email body
    body = f"""Hello,

You requested to reset your password for Apollo.

Click the link below to reset your password:
{reset_link}

This link will expire in 1 hour.

If you didn't request this, please ignore this email.

See you on the court! 🏓

— The Apollo Team
"""
    
    # Create message
    msg = MIMEMultipart()
    msg['From'] = email_from
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    # Send email
    try:
        logger.info(f"📧 Connecting to {smtp_server}:{smtp_port}...")
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
        server.starttls()
        logger.info(f"🔐 Logging in as {email_from}...")
        server.login(email_from, email_password)
        logger.info(f"📤 Sending reset email to {to_email}...")
        server.send_message(msg)
        server.quit()
        logger.info(f"✅ Reset email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send reset email to {to_email}: {e}")
        return False