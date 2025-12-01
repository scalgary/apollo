from fastapi import APIRouter, Depends, HTTPException, Response, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from services.auth_service import AuthService
from database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="templates")


# ============================================
# GET /auth/login - Afficher le formulaire
# ============================================

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    """Affiche la page de login"""
    return templates.TemplateResponse("login.html", {"request": request})


# ============================================
# POST /auth/login - Traiter le formulaire
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
            url="/auth/login?error=Invalid email or password",
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