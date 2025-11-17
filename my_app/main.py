
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles

from database import init_db, SessionLocal, engine, Base, get_db 
from sqlalchemy.orm import Session

from db_models import Event
from services.event_service import import_events_from_csv  # Pas "app.services"
from routes import auth, events, pages
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Créer l'application FastAPI
app = FastAPI(title="Apollo - Event Management System")

# Monte les fichiers statiques
app.mount("/static", StaticFiles(directory="static"), name="static")

# Inclure les routes
app.include_router(pages.router)
app.include_router(auth.router)
app.include_router(events.router)



@app.on_event("startup")
def startup_event():
    # 1. Créer toutes les tables D'ABORD
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created")
    
    # 2. PUIS importer les events du CSV
    db = SessionLocal()
    try:
        import_events_from_csv(db)
        print("✓ Events loaded from CSV")
    finally:
        db.close()

@app.get("/health")
def health_check():
    """Endpoint pour vérifier que l'API fonctionne"""
    return {"status": "ok"}

from database import SessionLocal, engine, Base
from services.event_service import import_events_from_csv

# Ajoute cet endpoint temporaire
@app.post("/dev/reset-events")
def dev_reset_events():
    """DEV ONLY - Clear and reimport events from CSV"""
    db = SessionLocal()
    try:
        # Delete all existing events
        from models import Event
        db.query(Event).delete()
        db.commit()
        
        # Reimport from CSV
        import_events_from_csv(db)
        return {"success": True, "message": "Events reset from CSV"}
    finally:
        db.close()


# backend/main.py
@app.get("/dev/view-events")
def dev_view_events(db: Session = Depends(get_db)):
    """DEV ONLY - View all events in database"""
    from models import Event
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