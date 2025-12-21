from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from services.auth_service import AuthService
from services.admin_service import AdminService
from services.event_service import EventService
from db_models import EventType

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# ============================================
# HELPER: Get authenticated admin user
# ============================================

def get_authenticated_admin_user(request: Request, db: Session):
    """
    Verify user is authenticated AND admin
    
    Returns:
        User object if authenticated admin
        
    Raises:
        HTTPException: If not authenticated or not admin
    """
    # 1. Check token
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # 2. Get user from token
    auth_service = AuthService(db)
    try:
        user = auth_service.get_current_user(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # 3. Check if admin
    admin_service = AdminService(db)
    if not admin_service.is_user_admin(user.id):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return user


# ============================================
# GET /admin - Admin page
# ============================================
@router.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request, db: Session = Depends(get_db)):
    """
    Display admin interface
    
    Accessible only to authenticated admins
    """
    try:
        user = get_authenticated_admin_user(request, db)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/login?error=Please login first", status_code=303)
        else:
            return RedirectResponse(url="/schedule?error=Admin access required", status_code=303)
    
    # Get data for template
    event_service = EventService(db)
    memberships = event_service.get_user_memberships_formatted(user.id)
    
    # Get all event types with deletion status
    admin_service = AdminService(db)
    event_types = db.query(EventType).order_by(EventType.id).all()
    event_type_count = len(event_types)
    
    # Add deletion info to each event type
    event_types_with_info = []
    for et in event_types:
        deletion_info = admin_service.can_delete_event_type(et.id)
        event_types_with_info.append({
            'event_type': et,
            'can_delete': deletion_info['can_delete'],
            'delete_reason': deletion_info['reason'],
            'future_events_count': deletion_info['future_events_count']
        })
    
    # NOUVEAU: Calculer les couleurs disponibles
    all_colors = [
        {'value': '#3b82f6', 'label': '🟦 Blue', 'name': 'blue'},
        {'value': '#f97316', 'label': '🟧 Orange', 'name': 'orange'},
        {'value': '#10b981', 'label': '🟩 Green', 'name': 'green'},
        {'value': '#8b5cf6', 'label': '🟪 Purple', 'name': 'purple'},
    ]
    
    # Couleurs déjà utilisées
    used_colors = [et.color for et in event_types]
    
    # Couleurs disponibles = toutes - utilisées
    available_colors = [c for c in all_colors if c['value'] not in used_colors]
    
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "user": user,
        "memberships": memberships,
        "event_types_with_info": event_types_with_info,
        "event_type_count": event_type_count,
        "available_colors": available_colors  # NOUVEAU
    })

# ============================================
# POST /api/admin/event-types - Create event type
# ============================================

@router.post("/api/admin/event-types")
def create_event_type(
    request: Request,
    display_name: str = Form(...),  # ← Plus besoin de event_type_name
    default_location: str = Form(...),
    default_time_start: str = Form(...),
    default_time_end: str = Form(...),
    default_max_capacity: int = Form(...),
    color: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Create a new event type
    
    Requires admin authentication
    """
    # 1. Check auth + admin
    try:
        user = get_authenticated_admin_user(request, db)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/login?error=Please login first", status_code=303)
        else:
            return RedirectResponse(url="/schedule?error=Admin access required", status_code=303)
    
    # 2. Create event type
    admin_service = AdminService(db)
    
    try:
        new_event_type = admin_service.create_event_type(
            display_name=display_name,  # ← Plus besoin de event_type_name
            default_location=default_location,
            default_time_start=default_time_start,
            default_time_end=default_time_end,
            default_max_capacity=default_max_capacity,
            color=color
        )
        
        # Success - redirect with message
        return RedirectResponse(
            url=f"/admin?success=Event type '{new_event_type.display_name}' created successfully#event-types",
            status_code=303
        )
        
    except ValueError as e:
        # Validation error - redirect with error message
        return RedirectResponse(
            url=f"/admin?error={str(e)}#event-types",
            status_code=303
        )
@router.post("/api/admin/event-types/{event_type_id}/delete")
def delete_event_type(
    event_type_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Delete an event type
    
    Requires admin authentication
    """
    # 1. Check auth + admin
    try:
        user = get_authenticated_admin_user(request, db)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/login?error=Please login first", status_code=303)
        else:
            return RedirectResponse(url="/schedule?error=Admin access required", status_code=303)
    
    # 2. Delete event type
    admin_service = AdminService(db)
    
    try:
        result = admin_service.delete_event_type(event_type_id)
        
        return RedirectResponse(
            url=f"/admin?success={result['message']}#event-types",
            status_code=303
        )
        
    except ValueError as e:
        return RedirectResponse(
            url=f"/admin?error={str(e)}#event-types",
            status_code=303
        )