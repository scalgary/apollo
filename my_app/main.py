from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from database import Base, engine, SessionLocal, get_db
from services.event_service import EventService

#from services.event_service import import_events_from_csv
from routes import auth, events, pages

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Exécuté au démarrage et à l'arrêt de l'app"""
    # === STARTUP ===
    # 1. Créer toutes les tables
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created")
    
    # 2. Importer les events du CSV
    db = SessionLocal()
    try:
        event_service = EventService()
        event_service.import_events_from_csv(db)
        print("✓ Events loaded from CSV")
    finally:
        db.close()
    
    yield  # L'app tourne
    
    # === SHUTDOWN ===
    print("✓ App shutting down")

# Créer l'app
app = FastAPI(lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(pages.router)
app.include_router(auth.router)
app.include_router(events.router)

# === HEALTH CHECK ===
@app.get("/health")
def health_check():
    """Endpoint pour vérifier que l'API fonctionne"""
    return {"status": "ok"}

# === DEV ENDPOINTS ===
@app.post("/dev/reset-events")
def dev_reset_events():
    """DEV ONLY - Clear and reimport events from CSV"""
    db = SessionLocal()
    try:
        from db_models import Event
        db.query(Event).delete()
        db.commit()
        
        event_service = EventService()
        event_service.import_events_from_csv(db)
        return {"success": True, "message": "Events reset from CSV"}
    finally:
        db.close()

@app.get("/dev/view-events")
def dev_view_events(db: Session = Depends(get_db)):
    """DEV ONLY - View all events in database"""
    from db_models import Event
    events = db.query(Event).all()
    return {
        "count": len(events),
        "events": [
            {
                "id": e.id,
                "date": str(e.date),
                "max_spots": e.max_spots,
                "confirmed_count": e.confirmed_count
            }
            for e in events
        ]
    }