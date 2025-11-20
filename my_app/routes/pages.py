
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from db_models import Event, Attendee
from utils import get_user_from_cookie

router = APIRouter()
templates = Jinja2Templates(directory="templates")
@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    """Page d'accueil - Redirige vers schedule"""
    user = get_user_from_cookie(request, db)
    
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    # Rediriger vers le nouveau schedule
    return RedirectResponse(url="/schedule", status_code=302)



@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    """Page de connexion"""
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    """Page d'inscription"""
    return templates.TemplateResponse("signup.html", {"request": request})

@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page(request: Request):
    """Page forgot password"""
    return templates.TemplateResponse("forgot_password.html", {"request": request})

@router.get("/reset-password", response_class=HTMLResponse)
def reset_password_page(request: Request, token: str = None):
    """Page reset password"""
    return templates.TemplateResponse("reset_password.html", {"request": request, "token": token})

