# backend/services/event_service.py
from sqlalchemy.orm import Session
from datetime import datetime
from db_models import Event
from utils import load_events

def import_events_from_csv(db: Session):
    """Import events from CSV into database"""
    events_data = load_events()
    imported_count = 0
    
    for event_data in events_data:
        try:
            event_id = int(event_data['id'])  # ← Convertir string en int
            
            # Check if event already exists
            existing = db.query(Event).filter(Event.id == event_id).first()
            
            if not existing:
                event = Event(
                    id=event_id,
                    date=datetime.strptime(event_data['date'], '%Y-%m-%d').date(),
                    max_spots=int(event_data['max_spots']),
                    confirmed_count=0
                )
                db.add(event)
                imported_count += 1
                
        except Exception as e:
            print(f"Error importing event {event_data.get('id')}: {e}")
            continue
    
    db.commit()
    print(f"✓ Imported {imported_count}/{len(events_data)} events from CSV")