from fastapi import APIRouter, Depends, HTTPException, Response, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from services.auth_service import AuthService
from database import get_db
import os
#router = APIRouter(prefix="/auth", tags=["auth"])
router = APIRouter()

templates = Jinja2Templates(directory="templates")


# ============================================
# GET /login - Afficher le formulaire
# ============================================

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    """Affiche la page de login"""
    return templates.TemplateResponse("login.html", {"request": request})


# ============================================
# POST /login - Traiter le formulaire
# ============================================

@router.post("/login")
def login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Authentifie l'utilisateur et set un cookie HTTP-only
    
    En cas de succès : redirige vers /schedule
    En cas d'échec : redirige vers /login avec message d'erreur
    """
    auth_service = AuthService(db)
    
    try:
        # Authentifier
        result = auth_service.authenticate(email, password)
        
        # Créer la réponse de redirection
        #redirect = RedirectResponse(url="/schedule", status_code=303)
        redirect = RedirectResponse(url="/schedule", status_code=303)

        # Set le cookie HTTP-only
        redirect.set_cookie(
            key="access_token",
            value=result["access_token"],
            httponly=True,      # JavaScript ne peut pas y accéder
            secure=False,       # True en production avec HTTPS
            samesite="lax",     # Protection CSRF
            max_age=60 * 60 * 24  # 24 heures (même durée que le token)
        )
        
        return redirect
        
    except ValueError as e:
        # Erreur d'authentification - rediriger vers login avec message
        return RedirectResponse(
            url="/login?error=Invalid email or password",
            status_code=303
        )


# ============================================
# Utility: Extraire le user depuis le cookie
# ============================================

def get_current_user_from_cookie(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Extrait le JWT token depuis le cookie et retourne le user
    
    À utiliser comme dépendance dans les autres routes :
    
    @router.get("/protected")
    def protected_route(user = Depends(get_current_user_from_cookie)):
        return {"user": user.email}
    
    Raises:
        HTTPException 401: Si token absent ou invalide
    """
    token = request.cookies.get("access_token")
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    auth_service = AuthService(db)
    
    try:
        user = auth_service.get_current_user(token)
        return user
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    

# ============================================
# GET /signup - Afficher le formulaire
# ============================================

@router.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    """Affiche la page de signup"""
    return templates.TemplateResponse("signup.html", {"request": request})


# ============================================
# POST /signup - Traiter le formulaire
# ============================================

@router.post("/signup")
def signup(
    email: str = Form(...),
    password: str = Form(...),
    display_name: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Crée un nouveau compte utilisateur
    
    En cas de succès : redirige vers /login avec message de succès
    En cas d'échec : redirige vers /signup avec message d'erreur
    """
    auth_service = AuthService(db)
    
    try:
        # Créer le compte
        auth_service.signup(email, password, display_name)  # ← Enlever "result ="
        
        # Rediriger vers login avec message de succès
        return RedirectResponse(
            url="/login?success=Account created successfully! Please login.",
            status_code=303
        )
        
    except ValueError as e:
        # Erreur - rediriger vers signup avec message
        return RedirectResponse(
            url=f"/signup?error={str(e)}",
            status_code=303
        )    

# Dans routes/auth.py, ajoute :

@router.get("/welcome", response_class=HTMLResponse)
def welcome_page(
    request: Request,
    user = Depends(get_current_user_from_cookie)
):
    """Page temporaire après login"""
    return templates.TemplateResponse("welcome.html", {
        "request": request,
        "user": user
    })

@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page(request: Request):  # ← Enlever le "user = Depends(...)"
    """Affiche la page forgot password"""
    return templates.TemplateResponse("forgot_password.html", {
        "request": request
        # Pas besoin de passer "user" ici
    })


# ============================================
# POST /forgot-password - Envoyer reset link
# ============================================

@router.post("/forgot-password")
def forgot_password(
    email: str = Form(...),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Génère un token de reset et envoie l'email (ou log en dev)
    """
    from services.email_service import EmailService
    
    auth_service = AuthService(db)
    email_service = EmailService()
    
    try:
        # Générer le token
        reset_token = auth_service.create_reset_token(email)
        
        # Construire le lien de reset
        # En prod, utiliser le vrai domaine
        base_url = os.getenv('BASE_URL', 'http://localhost:8000')
        reset_link = f"{base_url}/reset-password?token={reset_token}"
        # AJOUTE CE PRINT ICI ⬇️
        print("=" * 80)
        print(f"🔗 RESET LINK: {reset_link}")
        print("=" * 80)

        # Envoyer l'email (ou logger en dev)
        email_service.send_reset_email(email, reset_link)
        
        # Rediriger avec message de succès
        return RedirectResponse(
            url="/forgot-password?success=Reset link sent! Check your email (or console in dev mode).",
            status_code=303
        )
        
    except ValueError as e:
        # User n'existe pas - mais on ne révèle pas cette info pour la sécurité
        # On affiche le même message de succès
        return RedirectResponse(
            url="/forgot-password?success=If an account exists with this email, you will receive a reset link.",
            status_code=303
        )


# ============================================
# GET /reset-password - Afficher formulaire
# ============================================

@router.get("/reset-password", response_class=HTMLResponse)
def reset_password_page(
    request: Request,
    token: str
):
    """Affiche le formulaire de reset password"""
    return templates.TemplateResponse("reset_password.html", {
        "request": request,
        "token": token
    })


# ============================================
# POST /reset-password - Traiter nouveau password
# ============================================

@router.post("/reset-password")
def reset_password_submit(
    token: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Reset le password avec le token
    """
    auth_service = AuthService(db)
    
    try:
        # Reset le password
        auth_service.reset_password(token, new_password)
        
        # Rediriger vers login avec succès
        return RedirectResponse(
            url="/login?success=Password reset successful! Please login with your new password.",
            status_code=303
        )
        
    except ValueError as e:
        # Token invalide ou expiré
        return RedirectResponse(
            url="/forgot-password?error=Invalid or expired reset link. Please request a new one.",
            status_code=303
        )
    
@router.get("/logout")
def logout():
    """
    Déconnecte l'utilisateur en supprimant le cookie JWT
    
    Redirige vers /login
    """
    # Créer la réponse de redirection
    redirect = RedirectResponse(url="/login", status_code=303)
    
    # Supprimer le cookie en le mettant à expiration immédiate
    redirect.delete_cookie(
        key="access_token",
        httponly=True,
        secure=False,  # True en production avec HTTPS
        samesite="lax"
    )
    
    return redirect