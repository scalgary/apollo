from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from database import Base, engine, SessionLocal, get_db
from services.auth_service import AuthService
from services.event_service import EventService
from services.admin_service import AdminService

from fastapi.responses import RedirectResponse
from routes import registrations  # ← Import
from routes import messages
from routes import admin

#from services.event_service import import_events_from_csv
from routes import auth, events
#, events, pages

@asynccontextmanager
async def lifespan(app: FastAPI):
    import os
    USE_CSV = os.getenv('USE_CSV_LOADER', 'false').lower() == 'true'
    
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created")
    db = SessionLocal()
    try:
        event_service = EventService(db)
        admin_service = AdminService(db)

        # 1. Event types
        types_count = event_service.import_event_types_from_csv()
        print(f"✓ {types_count} Event types loaded")

        # 2. Events
        events_count = event_service.import_events_from_csv()
        print(f"✓ {events_count} Events loaded")
        
        # 3. Admins
        admins_count = admin_service.import_admins_from_csv()
        print(f"✓ {admins_count} Admins loaded")
        
        # 4. Friends (CSV loader if flag enabled)
        if USE_CSV:
            friends_count = admin_service.import_friends_from_csv()
            print(f"✓ {friends_count} Friends loaded from CSV")
        else:
            print("✓ Friends management via database only")

    finally:
        db.close()

    yield
    print("✓ App shutting down")
# Créer l'app
app = FastAPI(lifespan=lifespan)

# Mount static files

app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
# app.include_router(pages.router)
app.include_router(auth.router)
app.include_router(events.router)
app.include_router(registrations.router)  # ← Enregistrer le router
app.include_router(messages.router)
app.include_router(admin.router)


@app.get("/")
async def root():
    return RedirectResponse(url="/login", status_code=303)
# app.include_router(events.router)

# === HEALTH CHECK ===
# @app.get("/health")
# def health_check():
    # """Endpoint pour vérifier que l'API fonctionne"""
    # return {"status": "ok"}

# === DEV ENDPOINTS ===
# @app.post("/dev/reset-events")
# def dev_reset_events():
    # db = SessionLocal()
    # try:
    #     from db_models import Event, EventType

    #     # Supprimer dans l'ordre (events avant types à cause FK)
    #     db.query(Event).delete()
    #     db.query(EventType).delete()
    #     db.commit()

    #     event_service = EventService()
    #     types_count = event_service.import_event_types_from_csv(db)
    #     events_count = event_service.import_events_from_csv(db)

#         return {
#             "success": True,
#             "message": f"{types_count} types, {events_count} events loaded"
#         }
#     finally:
#         db.close()

# @app.get("/dev/view-events")
# def dev_view_events(db: Session = Depends(get_db)):
#     """DEV ONLY - View all events in database"""
#     from db_models import Event
#     events = db.query(Event).all()
#     return {
#         "count": len(events),
#         "events": [
#             {
#                 "id": e.id,
#                 "date": str(e.date),
#                 "max_spots": e.max_spots,
#                 "confirmed_count": e.confirmed_count
#             }
#             for e in events
#         ]
#     }