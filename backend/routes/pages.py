
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from models import Event, Attendee
from utils import get_user_from_cookie

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    """Page d'accueil - Dashboard des événements"""
    user = get_user_from_cookie(request, db)
    
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    events = db.query(Event).order_by(Event.date).all()
    user_statuses = {}
    for event in events:
        attendee = db.query(Attendee).filter(
            Attendee.event_id == event.id,
            Attendee.user_id == user.id
        ).first()
        user_statuses[event.id] = attendee.status if attendee else None
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "events": events,
        "user_statuses": user_statuses
    })

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
