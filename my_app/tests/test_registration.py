

def test_create_attendee_going(full_member_user, punch_card_user, db):
    from db_models import Event, User, Attendee
    from datetime import date

    event1 = Event(
        date=date(2025, 11, 25),
        max_spots=20
    )
    event2 = Event(
        date=date(2025, 11, 26),
        max_spots=2
    )
    db.add(event1)
    db.add(event2)
    db.commit()
    
    # Créer attendee pour full_member_user seulement
    attendee = Attendee(user_id=full_member_user.id, event_id=event2.id)
    db.add(attendee)
    db.commit()
    db.refresh(attendee)
    
    # ASSERT - full_member_user est inscrit
    assert attendee.id is not None
    assert attendee.user_id == full_member_user.id
    assert attendee.event_id == event2.id
    assert attendee.status == 'going'
    
    # ASSERT - punch_card_user N'est PAS inscrit
    punch_attendee = db.query(Attendee).filter(
        Attendee.user_id == punch_card_user.id,
        Attendee.event_id == event2.id
    ).first()
    
    assert punch_attendee is None  # ← Vérifier qu'il n'existe pas




def test_user_attends_multiple_events(full_member_user,db):
    from db_models import Event, User, Attendee
    from datetime import date  # ← Ajouter cet import


    event1 = Event(
        date=date(2025, 11, 25),
        max_spots=20
    )
    event2 = Event(
        date=date(2025, 11, 26),
        max_spots=2
    )
    event3 = Event(
        date=date(2025, 11, 28),
        max_spots=2)
    db.add(event1)
    db.add(event2)
    db.add(event3)

    db.commit()
    attendee1 = Attendee(user_id=full_member_user.id, event_id=event1.id)
    attendee2 = Attendee(user_id=full_member_user.id, event_id=event2.id)
    attendee3 = Attendee(user_id=full_member_user.id, event_id=event3.id)
    db.add(attendee1)
    db.add(attendee2)
    db.add(attendee3)
    db.commit()

    # BONUS - Compter tous les users
    total_attendees = db.query(Attendee).count()
    assert total_attendees == 3, "Devrait y avoir exactement 3 attendees"
    # Tu pourrais vérifier les attendees de CE user
    user1_attendees = db.query(Attendee).filter_by(user_id=full_member_user.id).count()
    assert user1_attendees == 3, "User1 devrait avoir 3 inscriptions" 


def test_mock_auth_works(client, db, test_event, punch_card_user, mock_auth_punch_card):
    """
    Test: Vérifier que l'inscription fonctionne avec le mock
    """
    
    # ARRANGE - État initial
    initial_credits = punch_card_user.remaining_credits
    assert initial_credits == 3, "Le user devrait avoir 3 crédits au départ"
    
    # ACT - S'inscrire
    response = client.post(f"/register/{test_event.id}")
    
    # ASSERT
    
    # 1. Pas d'erreur d'authentification
    assert response.status_code != 401, "Le mock devrait bypasser l'auth"
    
    # 2. Un Attendee a été créé
    from db_models import Attendee
    attendee = db.query(Attendee).filter_by(
        user_id=punch_card_user.id,
        event_id=test_event.id
    ).first()
    
    assert attendee is not None, "Un attendee devrait être créé"
    assert attendee.status == 'going', "Le status devrait être 'going'"
    
    # 3. Les crédits ont diminué
    db.refresh(punch_card_user)
    assert punch_card_user.remaining_credits == 2, f"Les crédits devraient passer de 3 à 2, mais sont à {punch_card_user.remaining_credits}"
    
    print(f"✓ Inscription réussie! Crédits: {initial_credits} → {punch_card_user.remaining_credits}")


