# backend/scripts/import_data.py
import sys
sys.path.append('..')

from database import SessionLocal
from services.event_service import import_events_from_csv

if __name__ == "__main__":
    db = SessionLocal()
    try:
        import_events_from_csv(db)
        print("✓ Data imported successfully")
    finally:
        db.close()