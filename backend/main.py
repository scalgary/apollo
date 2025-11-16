
from fastapi import FastAPI
from database import init_db, SessionLocal
from models import Event
from events_data import EVENTS
from routes import auth, events, pages
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Créer l'application FastAPI
app = FastAPI(title="Apollo - Event Management System")

# Inclure les routes
app.include_router(pages.router)
app.include_router(auth.router)
app.include_router(events.router)

@app.on_event("startup")
def startup():
    """Initialiser la base de données et créer les événements"""
    # Créer les tables
    init_db()
    
    # Auto-créer les événements depuis events_data.py
    db = SessionLocal()
    try:
        for event_data in EVENTS:
            existing = db.query(Event).filter(Event.date == event_data["date"]).first()
            if not existing:
                event = Event(
                    date=event_data["date"],
                    max_spots=event_data["max_spots"],
                    confirmed_count=0
                )
                db.add(event)
        
        db.commit()
        logger.info(f"✅ {len(EVENTS)} events initialized")
    finally:
        db.close()

@app.get("/health")
def health_check():
    """Endpoint pour vérifier que l'API fonctionne"""
    return {"status": "ok"}
