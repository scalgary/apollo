from db_models import Event, Attendee, User
from utils import get_password_hash

def test_register_to_event(client, test_user_email, test_password, db):
    """Test inscription à un événement"""
    # Créer user directement en DB (pas via signup)
    hashed_pw = get_password_hash(test_password)
    user = User(email=test_user_email, hashed_password=hashed_pw)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Login
    response = client.post("/login", data={
        "email": test_user_email,
        "password": test_password
    })
    
    # Créer événement
    event = Event(date="2025-12-25", max_spots=20, confirmed_count=0)
    db.add(event)
    db.commit()
    db.refresh(event)
    
    # S'inscrire
    response = client.post(f"/register/{event.id}", follow_redirects=False)
    
    assert response.status_code == 302
    
    # Vérifier inscription
    attendee = db.query(Attendee).filter(
        Attendee.event_id == event.id,
        Attendee.user_id == user.id
    ).first()
    assert attendee is not None
    assert attendee.status == "going"