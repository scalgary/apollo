# backend/scripts/import_data.py
import sys
sys.path.append('..')

from database import SessionLocal
from services.event_service import EventService


if __name__ == "__main__":
    db = SessionLocal()
    try:
        event_service = EventService()
        event_service.import_events_from_csv(db)
        print("✓ Data imported successfully")
    finally:
        db.close()