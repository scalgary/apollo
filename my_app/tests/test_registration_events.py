from db_models import Event, Attendee, User

def test_register_to_event(client, create_user, db):
    """Test inscription à un événement par un full_member"""
    from datetime import date, timedelta
    
    # Créer un user avec l'email de la whitelist (user1@example.com est full_member pour open_play)
    user = create_user(
        email="user1@example.com",
        password="testpass123",
        event_type_id=1,  # open_play
        membership_type="full_member"
    )
    
    # Login
    response = client.post("/login", data={
        "email": user.email,
        "password": user.plain_password
    }, follow_redirects=False)
    
    assert response.status_code == 302
    assert "access_token" in response.cookies
    
    # Créer événement open_play
    event = Event(
        event_type_id=1,
        date=date.today() + timedelta(days=5)
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    
    # S'inscrire
    response = client.post(f"/register/{event.id}", follow_redirects=False)
    
    assert response.status_code == 302
    assert "/schedule" in response.headers["location"]
    
    # Vérifier inscription
    attendee = db.query(Attendee).filter(
        Attendee.event_id == event.id,
        Attendee.user_id == user.id
    ).first()
    
    assert attendee is not None
    assert attendee.status == "going"
    assert attendee.credit_used == 0
    
    # Vérifier confirmed_count
    db.refresh(event)
    assert event.confirmed_count == 1
    
    print(f"✓ User inscrit avec succès")