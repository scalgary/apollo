def test_create_attendee_going(full_member_user, punch_card_user, db):
    """Test: Créer des attendees pour des events"""
    from db_models import Event, Attendee
    from datetime import date

    event1 = Event(
        event_type_id=1,  # ← NOUVEAU
        date=date(2025, 11, 25)
    )
    event2 = Event(
        event_type_id=1,  # ← NOUVEAU
        date=date(2025, 11, 26)
    )
    db.add(event1)
    db.add(event2)
    db.commit()
    
    # Créer attendee pour full_member_user
    attendee = Attendee(user_id=full_member_user.id, event_id=event2.id)
    db.add(attendee)
    db.commit()
    db.refresh(attendee)
    
    # ASSERT
    assert attendee.id is not None
    assert attendee.user_id == full_member_user.id
    assert attendee.event_id == event2.id
    assert attendee.status == 'going'
    assert attendee.credit_used == 0  # ← NOUVEAU: full_member ne consomme pas de crédit
    
    # punch_card_user n'est PAS inscrit
    punch_attendee = db.query(Attendee).filter(
        Attendee.user_id == punch_card_user.id,
        Attendee.event_id == event2.id
    ).first()
    
    assert punch_attendee is None
    
    print("✓ Attendee créé, credit_used=0 pour full_member")

def test_user_attends_multiple_events(full_member_user, db):
    """Test: Un user s'inscrit à plusieurs events"""
    from db_models import Event, Attendee
    from datetime import date

    event1 = Event(event_type_id=1, date=date(2025, 11, 25))
    event2 = Event(event_type_id=1, date=date(2025, 11, 26))
    event3 = Event(event_type_id=1, date=date(2025, 11, 28))
    
    db.add_all([event1, event2, event3])
    db.commit()
    
    attendee1 = Attendee(user_id=full_member_user.id, event_id=event1.id)
    attendee2 = Attendee(user_id=full_member_user.id, event_id=event2.id)
    attendee3 = Attendee(user_id=full_member_user.id, event_id=event3.id)
    
    db.add_all([attendee1, attendee2, attendee3])
    db.commit()

    # Vérifications
    total_attendees = db.query(Attendee).count()
    assert total_attendees == 3
    
    user_attendees = db.query(Attendee).filter_by(user_id=full_member_user.id).count()
    assert user_attendees == 3
    
    print("✓ User inscrit à 3 events")
def test_mock_auth_works(client, db, test_event, punch_card_user, mock_auth_punch_card):
    """Test: L'inscription consomme un crédit pour punch_card à J-7"""
    from db_models import Attendee, UserEventTypeMembership
    from datetime import date, timedelta
    
    # IMPORTANT: Modifier la date de l'événement pour être à J-7 ou moins
    # Sinon le punch_card ira en waitlist automatiquement
    test_event.date = date.today() + timedelta(days=5)  # Dans 5 jours
    db.commit()
    
    # ARRANGE - Vérifier crédits initiaux
    membership = db.query(UserEventTypeMembership).filter_by(
        user_id=punch_card_user.id,
        event_type_id=1
    ).first()
    
    assert membership.total_credits_purchased == 10
    assert membership.remaining_credits == 10, "Devrait avoir 10 crédits au départ"
    
    # ACT - S'inscrire
    response = client.post(f"/register/{test_event.id}")
    
    # ASSERT
    assert response.status_code != 401, "Mock devrait bypasser auth"
    
    # Attendee créé
    attendee = db.query(Attendee).filter_by(
        user_id=punch_card_user.id,
        event_id=test_event.id
    ).first()
    
    assert attendee is not None, "Attendee devrait être créé"
    assert attendee.status == 'going', "Status devrait être 'going' (event dans 5 jours)"
    assert attendee.credit_used == 1, "credit_used devrait être 1"
    
    # Vérifier crédits restants
    db.refresh(membership)
    assert membership.remaining_credits == 9, f"Devrait avoir 9 crédits, mais a {membership.remaining_credits}"
    
    print(f"✓ Inscription réussie! Crédits: 10 → 9")