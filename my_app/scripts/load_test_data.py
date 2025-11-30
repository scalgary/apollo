"""
Script pour charger les données de test depuis les CSV dans la DB.
Charge : event_types et events
"""
import sys
import os
import csv
from datetime import datetime

# Force connexion Docker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database import engine, Base
from db_models import EventType, Event
from sqlalchemy.orm import Session

# Chemins des CSV
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
EVENT_TYPE_CSV = os.path.join(DATA_DIR, 'event_types.csv')
EVENTS_CSV = os.path.join(DATA_DIR, 'events.csv')

def reset_database():
    """Supprime et recrée toutes les tables."""
    print("🗑️  Suppression des tables existantes...")
    Base.metadata.drop_all(bind=engine)
    
    print("🔨 Création des nouvelles tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables créées!\n")

def load_event_types_from_csv():
    """Charge les event_types depuis le CSV."""
    with Session(engine) as session:
        print("📝 Chargement des event_types depuis CSV...")
        
        with open(EVENT_TYPE_CSV, 'r') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                event_type = EventType(
                    name=row['name'].strip(),
                    display_name=row['display_name'].strip(),
                    default_location=row['default_location'].strip(),
                    default_time_start=row['default_time_start'].strip(),
                    default_time_end=row['default_time_end'].strip(),
                    default_max_capacity=int(row['default_max_capacity']),
                    color=row['color'].strip()
                )
                session.add(event_type)
                count += 1
                print(f"   ✓ {event_type.name} → {event_type.display_name}")
            
            session.commit()
            print(f"✅ {count} event_types chargés!\n")

def load_events_from_csv():
    """Charge les events depuis le CSV."""
    with Session(engine) as session:
        print("📝 Chargement des events depuis CSV...")
        
        # D'abord récupérer les event_types pour mapper les noms aux IDs
        event_types = {et.name: et.id for et in session.query(EventType).all()}
        
        with open(EVENTS_CSV, 'r') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                event_type_name = row['event_type_name'].strip()
                date_str = row['date'].strip()
                
                if event_type_name not in event_types:
                    print(f"   ⚠️  Event type '{event_type_name}' non trouvé, skip")
                    continue
                
                event = Event(
                    event_type_id=event_types[event_type_name],
                    date=datetime.strptime(date_str, '%Y-%m-%d').date()
                )
                session.add(event)
                count += 1
                print(f"   ✓ {event_type_name} le {date_str}")
            
            session.commit()
            print(f"✅ {count} events chargés!\n")

if __name__ == '__main__':
    print("=" * 60)
    print("CHARGEMENT DES DONNÉES DE TEST")
    print("=" * 60 + "\n")
    
    reset_database()
    load_event_types_from_csv()
    load_events_from_csv()
    
    print("🎉 Données chargées!")
    print("\n📌 Ouvre DBeaver et vérifie:")
    print("   - Table event_types : 2 lignes")
    print("   - Table events : 5 lignes")
    print("   - Table users : vide")
    print("   - Table user_event_type_memberships : vide")