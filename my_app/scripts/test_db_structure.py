"""
Script pour recréer la base de données avec la nouvelle structure.
Supprime toutes les tables existantes et recrée tout.
"""
import sys
import os
# Au lieu de localhost, utilise l'URL d'origine
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ['DATABASE_URL'] = 'postgresql://apollo:apollo123@db:5432/apollo_db'# Ajoute le dossier parent au path pour pouvoir importer


from database import engine, Base
from db_models import User, EventType, UserEventTypeMembership, Event, Attendee, PasswordReset
from sqlalchemy.orm import Session

def reset_database():
    """Supprime et recrée toutes les tables."""
    print("🗑️  Suppression des tables existantes...")
    Base.metadata.drop_all(bind=engine)
    
    print("🔨 Création des nouvelles tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables créées avec succès!\n")

def insert_event_types():
    """Insère les 2 types d'événements fixes."""
    with Session(engine) as session:
        print("📝 Insertion des event_types...")
        
        # Type 1: Jeudi intérieur
        open_play = EventType(
            name='open_play',
            display_name='Intérieur',
            default_location='Calgary Indoor Sports Arena',
            default_time_start='19:00',
            default_time_end='21:00',
            default_max_capacity=20,
            color='#4A90E2'
        )
        
        # Type 2: Dimanche extérieur
        competitive = EventType(
            name='competitive',
            display_name='Extérieur',
            default_location='Riley Park Outdoor Courts',
            default_time_start='14:00',
            default_time_end='16:00',
            default_max_capacity=16,
            color='#7ED321'
        )
        
        session.add(open_play)
        session.add(competitive)
        session.commit()
        
        print("✅ Event types insérés!")
        print(f"   ID {open_play.id}: {open_play.name} → {open_play.display_name}")
        print(f"   ID {competitive.id}: {competitive.name} → {competitive.display_name}\n")

def show_tables():
    """Affiche les tables créées."""
    from sqlalchemy import inspect
    inspector = inspect(engine)
    
    print("📊 Tables créées dans la base de données:")
    for table_name in inspector.get_table_names():
        print(f"   - {table_name}")
    print()

if __name__ == '__main__':
    print("=" * 60)
    print("RECRÉATION DE LA BASE DE DONNÉES")
    print("=" * 60 + "\n")
    
    reset_database()
    insert_event_types()
    show_tables()
    
    print("🎉 Base de données prête!")
    print("\n📌 Prochaines étapes:")
    print("   1. Ouvre DBeaver")
    print("   2. Connecte-toi à: localhost:5432")
    print("   3. Base: apollo, User: apollo, Password: apollo123")
    print("   4. Vérifie les tables et la structure")