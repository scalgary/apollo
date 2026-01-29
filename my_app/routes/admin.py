from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from services.auth_service import AuthService
from services.admin_service import AdminService
from services.event_service import EventService
from db_models import EventType, Event
from pydantic import BaseModel
from utils import export_whitelist_to_csv, export_event_types_to_csv, export_events_to_csv
# Add after imports, before router
class ManageDatesRequest(BaseModel):
    event_type_id: int
    dates_to_add: list[str]
    dates_to_delete: list[str]

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
    
    # Calculate available colors
    all_colors = [
        {'value': '#3b82f6', 'label': '🟦 Blue', 'name': 'blue'},
        {'value': '#f97316', 'label': '🟧 Orange', 'name': 'orange'},
        {'value': '#10b981', 'label': '🟩 Green', 'name': 'green'},
        {'value': '#8b5cf6', 'label': '🟪 Purple', 'name': 'purple'},
    ]
    
    # Used colors
    used_colors = [et.color for et in event_types]
    
    # Available colors = all - used
    available_colors = [c for c in all_colors if c['value'] not in used_colors]
    
    # Get all users with memberships for Users tab
    users_with_memberships = admin_service.get_all_users_with_memberships()
    
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "user": user,
        "memberships": memberships,
        "event_types_with_info": event_types_with_info,
        "event_type_count": event_type_count,
        "available_colors": available_colors,
        "users_with_memberships": users_with_memberships
    })

# ============================================
# POST /api/admin/event-types - Create event type
# ============================================

@router.post("/api/admin/event-types")
def create_event_type(
    request: Request,
    display_name: str = Form(...),
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
            display_name=display_name,
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


# ============================================
# POST /api/admin/memberships/bulk-add - Bulk add memberships
# ============================================

@router.post("/api/admin/memberships/bulk-add")
def bulk_add_memberships(
    request: Request,
    event_type_id: int = Form(...),
    membership_type: str = Form(...),
    emails: str = Form(...),
    credits: int = Form(default=0),
    db: Session = Depends(get_db)
):
    """
    Add/update memberships for multiple users
    
    - Creates users if they don't exist
    - Updates existing memberships or creates new ones
    """
    # 1. Check auth + admin
    try:
        user = get_authenticated_admin_user(request, db)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/login?error=Please login first", status_code=303)
        else:
            return RedirectResponse(url="/schedule?error=Admin access required", status_code=303)
    
    # 2. Bulk add memberships
    admin_service = AdminService(db)
    
    try:
        result = admin_service.bulk_add_memberships(
            event_type_id=event_type_id,
            membership_type=membership_type,
            emails_text=emails,
            credits=credits
        )
        
        return RedirectResponse(
            url=f"/admin?success={result['message']}#users",
            status_code=303
        )
        
    except ValueError as e:
        return RedirectResponse(
            url=f"/admin?error={str(e)}#users",
            status_code=303
        )


# ============================================
# POST /api/admin/memberships/add-credits - Add credits to user
# ============================================

@router.post("/api/admin/memberships/add-credits")
def add_credits_to_user(
    request: Request,
    user_id: int = Form(...),
    event_type_id: int = Form(...),
    credits_to_add: int = Form(...),
    db: Session = Depends(get_db)
):
    """
    Add credits to specific user's punch card
    """
    # 1. Check auth + admin
    try:
        user = get_authenticated_admin_user(request, db)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/login?error=Please login first", status_code=303)
        else:
            return RedirectResponse(url="/schedule?error=Admin access required", status_code=303)
    
    # 2. Add credits
    admin_service = AdminService(db)
    
    try:
        result = admin_service.add_credits(
            user_id=user_id,
            event_type_id=event_type_id,
            credits_to_add=credits_to_add
        )
        
        return RedirectResponse(
            url=f"/admin?success={result['message']}#users",
            status_code=303
        )
        
    except ValueError as e:
        return RedirectResponse(
            url=f"/admin?error={str(e)}#users",
            status_code=303
        )
    
@router.post("/api/admin/events/bulk-create")
def bulk_create_events(
    request: Request,
    event_type_id: int = Form(...),
    dates: str = Form(...),
    db: Session = Depends(get_db)
):
    """Create multiple events for an event type"""
    try:
        user = get_authenticated_admin_user(request, db)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/login?error=Please login first", status_code=303)
        else:
            return RedirectResponse(url="/schedule?error=Admin access required", status_code=303)
    
    admin_service = AdminService(db)
    
    try:
        result = admin_service.bulk_create_events(event_type_id, dates)
        
        return RedirectResponse(
            url=f"/admin?success={result['message']}#dates",
            status_code=303
        )
        
    except ValueError as e:
        return RedirectResponse(
            url=f"/admin?error={str(e)}#dates",
            status_code=303
        )
    

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Add after imports
class ManageDatesRequest(BaseModel):
    event_type_id: int
    dates_to_add: list[str]
    dates_to_delete: list[str]

# Add these routes after bulk_create_events
@router.get("/api/admin/events/{event_type_id}/dates")
def get_event_dates(
    event_type_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Get all future dates for an event type"""
    try:
        user = get_authenticated_admin_user(request, db)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    from datetime import date
    
    events = db.query(Event).filter(
        Event.event_type_id == event_type_id,
        Event.date >= date.today()
    ).order_by(Event.date).all()
    
    dates = [str(e.date) for e in events]
    
    return JSONResponse(content={"dates": dates})


@router.post("/api/admin/events/manage-dates")
def manage_event_dates(
    request: Request,
    body: ManageDatesRequest,
    db: Session = Depends(get_db)
):
    """Add and delete event dates"""
    try:
        user = get_authenticated_admin_user(request, db)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    admin_service = AdminService(db)
    
    try:
        result = admin_service.manage_event_dates(
            event_type_id=body.event_type_id,
            dates_to_add=body.dates_to_add,
            dates_to_delete=body.dates_to_delete
        )
        
        return JSONResponse(content=result)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
from fastapi.responses import FileResponse
from utils import export_whitelist_to_csv, export_event_types_to_csv, export_events_to_csv

# Ajouter ces endpoints dans admin.py
# Dans admin.py
@router.get("/admin/export/whitelist")
async def download_whitelist(
    request: Request,
    db: Session = Depends(get_db)
):
    """Export whitelist as CSV"""
    try:
        user = get_authenticated_admin_user(request, db)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/login?error=Please login first", status_code=303)
        else:
            return RedirectResponse(url="/schedule?error=Admin access required", status_code=303)
    
    filepath = export_whitelist_to_csv(db)
    return FileResponse(filepath, filename="whitelist.csv", media_type="text/csv")


@router.get("/export/event-types")
async def download_event_types(
    request: Request,
    db: Session = Depends(get_db)
):
    """Export event types as CSV"""
    try:
        user = get_authenticated_admin_user(request, db)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/login?error=Please login first", status_code=303)
        else:
            return RedirectResponse(url="/schedule?error=Admin access required", status_code=303)
    
    filepath = export_event_types_to_csv(db)
    return FileResponse(filepath, filename="event_types.csv", media_type="text/csv")


@router.get("/export/events")
async def download_events(
    request: Request,
    db: Session = Depends(get_db)
):
    """Export events as CSV"""
    try:
        user = get_authenticated_admin_user(request, db)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/login?error=Please login first", status_code=303)
        else:
            return RedirectResponse(url="/schedule?error=Admin access required", status_code=303)
    
    filepath = export_events_to_csv(db)
    return FileResponse(filepath, filename="events.csv", media_type="text/csv")
from fastapi.responses import StreamingResponse
import zipfile
from io import BytesIO

@router.get("/export/all")
async def download_all_data(
    request: Request,
    db: Session = Depends(get_db)
):
    """Export all data as ZIP file"""
    # Vérifier auth admin
    try:
        user = get_authenticated_admin_user(request, db)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/login?error=Please login first", status_code=303)
        else:
            return RedirectResponse(url="/schedule?error=Admin access required", status_code=303)
    
    # Generate all CSV files
    whitelist_path = export_whitelist_to_csv(db)
    event_types_path = export_event_types_to_csv(db)
    events_path = export_events_to_csv(db)
    
    # Create ZIP in memory
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.write(whitelist_path, 'whitelist.csv')
        zip_file.write(event_types_path, 'event_types.csv')
        zip_file.write(events_path, 'events.csv')
    
    zip_buffer.seek(0)
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=apollo_data_export.zip"}
    )

@router.post("/api/admin/users/{user_id}/event-type/{event_type_id}/delete")
def delete_user_membership(
    user_id: int,
    event_type_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Delete a user's membership for specific event type"""
    try:
        user = get_authenticated_admin_user(request, db)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/login?error=Please login first", status_code=303)
        else:
            return RedirectResponse(url="/schedule?error=Admin access required", status_code=303)
    
    admin_service = AdminService(db)
    
    try:
        result = admin_service.delete_user_membership(user_id, event_type_id)
        
        return RedirectResponse(
            url=f"/admin?success={result['message']}#users",
            status_code=303
        )
        
    except ValueError as e:
        return RedirectResponse(
            url=f"/admin?error={str(e)}#users",
            status_code=303
        )
    

@router.get("/api/admin/debug/user/{user_id}/memberships")
def debug_user_memberships(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Debug - voir les memberships d'un user"""
    try:
        user = get_authenticated_admin_user(request, db)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    from db_models import UserEventTypeMembership, Friend
    
    # Check User
    user_obj = db.query(User).filter(User.id == user_id).first()
    if not user_obj:
        return {"error": "User not found"}
    
    # Check UserEventTypeMembership
    memberships = db.query(UserEventTypeMembership).filter(
        UserEventTypeMembership.user_id == user_id
    ).all()
    
    # Check Friends
    friends = db.query(Friend).filter(
        Friend.email == user_obj.email
    ).all()
    
    return {
        "user": {
            "id": user_obj.id,
            "email": user_obj.email,
            "display_name": user_obj.display_name
        },
        "memberships": [
            {
                "event_type_id": m.event_type_id,
                "membership_type": m.membership_type,
                "total_credits": m.total_credits_purchased,
                "remaining_credits": m.remaining_credits
            }
            for m in memberships
        ],
        "friends": [
            {
                "event_type_id": f.event_type_id,
                "membership_type": f.membership_type,
                "total_credits": f.total_credits_purchased
            }
            for f in friends
        ]
    }

@router.post("/api/admin/friends/delete")
def delete_friend_membership(
    request: Request,
    email: str = Form(...),
    event_type_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """Delete friend (not signed up) from whitelist"""
    try:
        user = get_authenticated_admin_user(request, db)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/login?error=Please login first", status_code=303)
        else:
            return RedirectResponse(url="/schedule?error=Admin access required", status_code=303)
    
    from db_models import Friend, EventType
    
    event_type = db.query(EventType).filter(EventType.id == event_type_id).first()
    if not event_type:
        return RedirectResponse(url="/admin?error=Event type not found#users", status_code=303)
    
    deleted = db.query(Friend).filter(
        Friend.email == email.lower(),
        Friend.event_type_id == event_type_id
    ).delete()
    
    db.commit()
    
    if deleted > 0:
        return RedirectResponse(
            url=f"/admin?success=Removed {email} from {event_type.display_name} whitelist#users",
            status_code=303
        )
    else:
        return RedirectResponse(
            url="/admin?error=Friend entry not found#users",
            status_code=303
        )