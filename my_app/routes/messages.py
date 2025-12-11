from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from services.auth_service import AuthService
from services.message_service import MessageService
from pydantic import BaseModel
from utils import MESSAGE_EMOJIS, COMMENT_EMOJIS


router = APIRouter()
templates = Jinja2Templates(directory="templates")


# ============================================
# MODELS PYDANTIC POUR VALIDATION
# ============================================

class CreateMessageRequest(BaseModel):
    content: str

class EditMessageRequest(BaseModel):
    content: str

class CreateCommentRequest(BaseModel):
    content: str

class EditCommentRequest(BaseModel):
    content: str


# ============================================
# HELPER: RÉCUPÉRER USER AUTHENTIFIÉ
# ============================================

def get_authenticated_user(request: Request, db: Session):
    """
    Helper pour récupérer le user authentifié depuis le cookie
    
    Raises:
        HTTPException: Si pas authentifié ou token invalide
    """
    token = request.cookies.get("access_token")
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    auth_service = AuthService(db)
    
    try:
        user = auth_service.get_current_user(token)
        return user
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ============================================
# PAGE HTML: AFFICHAGE MESSAGES
# ============================================

@router.get("/community")
def community_pages(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Page principale des messages et commentaires
    
    Affiche:
    - Tous les messages (ordre chronologique inversé)
    - Leurs commentaires
    - Formulaires pour poster/éditer
    """
    
    # Vérifier authentification
    token = request.cookies.get("access_token")
    
    if not token:
        return RedirectResponse(url="/login?error=Please login first", status_code=303)
    
    auth_service = AuthService(db)
    
    try:
        user = auth_service.get_current_user(token)
    except ValueError:
        return RedirectResponse(url="/login?error=Session expired", status_code=303)
    
    # Récupérer les memberships (AJOUTER CETTE LIGNE)
    from services.event_service import EventService
    event_service = EventService(db)
    memberships = event_service.get_user_memberships_formatted(user.id)

    
    # Récupérer tous les messages avec commentaires
    message_service = MessageService(db)
    messages = message_service.get_all_messages_with_comments()
    
    # Render template
    return templates.TemplateResponse("test.html", {
        "request": request,
        "user": user,
        "memberships": memberships,
        "messages": messages,
        "message_emojis": MESSAGE_EMOJIS,  # ← AJOUTER
        "comment_emojis": COMMENT_EMOJIS   # ← AJOUTER
    })



# ============================================
# API: MESSAGES CRUD
# ============================================

@router.post("/api/messages")
def create_message(
    request: Request,
    body: CreateMessageRequest,
    db: Session = Depends(get_db)
):
    """
    Créer un nouveau message
    
    Returns:
        JSON avec le message créé
    """
    user = get_authenticated_user(request, db)
    message_service = MessageService(db)
    
    try:
        message = message_service.create_message(user.id, body.content)
        
        return JSONResponse(content={"success": True, "message": message}, status_code=201)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    



@router.put("/api/messages/{message_id}")
def edit_message(
    message_id: int,
    request: Request,
    body: EditMessageRequest,
    db: Session = Depends(get_db)
):
    """
    Éditer un message existant
    
    Permissions: Seulement l'auteur
    """
    user = get_authenticated_user(request, db)
    message_service = MessageService(db)
    
    try:
        message = message_service.edit_message(message_id, user.id, body.content)
        return JSONResponse(content={"success": True, "message": message})
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/api/messages/{message_id}")
def delete_message(
    message_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Supprimer un message
    
    Permissions: Auteur OU admin
    """
    user = get_authenticated_user(request, db)
    message_service = MessageService(db)
    
    try:
        result = message_service.delete_message(message_id, user.id)
        return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


# ============================================
# API: COMMENTAIRES CRUD
# ============================================

@router.post("/api/messages/{message_id}/comments")
def create_comment(
    message_id: int,
    request: Request,
    body: CreateCommentRequest,
    db: Session = Depends(get_db)
):
    """
    Créer un commentaire sur un message
    
    Returns:
        JSON avec le commentaire créé
    """
    user = get_authenticated_user(request, db)
    message_service = MessageService(db)
    
    try:
        comment = message_service.create_comment(message_id, user.id, body.content)
        return JSONResponse(content={"success": True, "comment": comment}, status_code=201)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/api/comments/{comment_id}")
def edit_comment(
    comment_id: int,
    request: Request,
    body: EditCommentRequest,
    db: Session = Depends(get_db)
):
    """
    Éditer un commentaire existant
    
    Permissions: Seulement l'auteur
    """
    user = get_authenticated_user(request, db)
    message_service = MessageService(db)
    
    try:
        comment = message_service.edit_comment(comment_id, user.id, body.content)
        return JSONResponse(content={"success": True, "comment": comment})
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/api/comments/{comment_id}")
def delete_comment(
    comment_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Supprimer un commentaire
    
    Permissions: Auteur OU admin
    """
    user = get_authenticated_user(request, db)
    message_service = MessageService(db)
    
    try:
        result = message_service.delete_comment(comment_id, user.id)
        return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


# ============================================
# API: ADMIN - CLEANUP MANUEL (OPTIONNEL)
# ============================================

@router.post("/api/messages/cleanup")
def cleanup_messages(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Trigger manuel du cleanup (pour admins)
    
    Normalement exécuté automatiquement par APScheduler
    """
    user = get_authenticated_user(request, db)
    message_service = MessageService(db)
    
    # Vérifier que user est admin
    if not message_service.admin_service.is_user_admin(user.id):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = message_service.cleanup_old_messages()
    return JSONResponse(content=result)