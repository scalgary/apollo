from db_models import Event, Attendee, User
from utils import get_password_hash

def test_register_to_event(client, test_user_email, test_password,full_member_user, db):
    """Test inscription à un événement"""
    from datetime import date  # ← Ajouter cet import

    
    # Login
    response = client.post("/login", data={
        "email": full_member_user.email,
        "password": full_member_user.plain_password
    })

    # Créer événement
    event = Event(date=date(2025, 12, 25), max_spots=20, confirmed_count=0)
    db.add(event)
    db.commit()
    db.refresh(event)
    
    # S'inscrire
    response = client.post(f"/register/{event.id}", follow_redirects=False)
    
    assert response.status_code == 302
    
    # Vérifier inscription
    attendee = db.query(Attendee).filter(
        Attendee.event_id == event.id,
        Attendee.user_id == full_member_user.id
    ).first()
    assert attendee is not None
    assert attendee.status == "going"