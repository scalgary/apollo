import sys
import os

# Ajouter le dossier parent (app/) au path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_models import User, Event, Attendee, EventType

# Les variables d'env sont déjà dans le container Docker
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in environment variables")
    sys.exit(1)

print(f"Connecting to database...")

# Créer la connexion
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()

# Event ID à checker
if len(sys.argv) > 1:
    event_id = int(sys.argv[1])
else:
    event_id = 1

print(f"Checking event ID: {event_id}\n")

# Query pour récupérer l'événement
event = db.query(Event, EventType).join(
    EventType, Event.event_type_id == EventType.id
).filter(Event.id == event_id).first()

if not event:
    print(f"❌ Event {event_id} not found")
    db.close()
    sys.exit(1)

event_obj, event_type = event

print(f"{'='*60}")
print(f"EVENT: {event_type.display_name}")
print(f"DATE: {event_obj.date}")
print(f"LOCATION: {event_type.default_location}")
print(f"TIME: {event_type.default_time_start} - {event_type.default_time_end}")
print(f"CAPACITY: {event_obj.confirmed_count}/{event_type.default_max_capacity}")
print(f"{'='*60}\n")

# Query pour les attendees
attendees = db.query(Attendee, User).join(
    User, Attendee.user_id == User.id
).filter(
    Attendee.event_id == event_id
).order_by(Attendee.status, Attendee.registered_at).all()

if not attendees:
    print("ℹ️  No attendees found for this event.\n")
    db.close()
    sys.exit(0)

# Séparer going, waitlist et not_going
going = [(a, u) for a, u in attendees if a.status == 'going']
waitlist = [(a, u) for a, u in attendees if a.status == 'waitlist']
not_going = [(a, u) for a, u in attendees if a.status == 'not_going']

# Afficher GOING
if going:
    print(f"✅ GOING ({len(going)}/{event_type.default_max_capacity}):")
    print("-" * 60)
    for attendee, user in going:
        credit_info = f"💳 Credit used" if attendee.credit_used else "🎫 Full member"
        print(f"  • {user.display_name:<25} {credit_info}")
        print(f"    {user.email}")
        print(f"    Registered: {attendee.registered_at}")
        print()

# Afficher WAITLIST
if waitlist:
    print(f"⏳ WAITLIST ({len(waitlist)}):")
    print("-" * 60)
    for idx, (attendee, user) in enumerate(waitlist, start=1):
        print(f"  #{idx} {user.display_name} ({user.email})")
        print(f"     Registered: {attendee.registered_at}")
        print()

# Afficher NOT GOING
if not_going:
    print(f"❌ NOT GOING ({len(not_going)}):")
    print("-" * 60)
    for attendee, user in not_going:
        print(f"  • {user.display_name} ({user.email})")
    print()

# Résumé
print("=" * 60)
print(f"📊 SUMMARY:")
print(f"  Total registrations: {len(attendees)}")
print(f"  • Going: {len(going)}")
print(f"  • Waitlist: {len(waitlist)}")
print(f"  • Not going: {len(not_going)}")
print(f"  Available spots: {event_type.default_max_capacity - len(going)}")
print("=" * 60)
print()

db.close()