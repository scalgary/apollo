# tests/test_event.py

def test_create_event(db):
    """
    Test simple: créer un event
    """
    from db_models import Event
    
    # ARRANGE - Préparer les données
    from datetime import date  # ← Ajouter cet import
    
    date = date(2025, 12, 25)  # ✅ Objet date
    max_spots = 20
    
    # ACT - Créer le user
    event = Event(
        date=date,
        max_spots=max_spots
    )
    
    db.add(event)
    db.commit()
    db.refresh(event)  # Recharge les données depuis la DB (pour avoir l'id)
    
    # ASSERT - Vérifier
    assert event.id is not None, "Le user devrait avoir un ID après commit"
    assert event.date == date
    assert event.max_spots == max_spots
    assert event.confirmed_count==0
 
    
    print(f"✓ Event créé avec l'ID: {event.id}")




def test_create_events(db):
    """
    Test simple: créer un event
    """
    from db_models import Event
    from datetime import date  # ← Ajouter cet import
    
    event_date1 = date(2025, 12, 25)  # ✅ Objet date
    event_date2 = date(2025, 12, 26)  # ✅ Objet date


    # ACT - Créer le user
    event1 = Event(
        date=event_date1,
        max_spots=20
    )
    event2 = Event(
        date=event_date2,
        max_spots=2
    )
    
    db.add(event1)
    db.add(event2)
    db.commit()
    # ACT - Les retrouver via des requêtes
    found_nov = db.query(Event).filter_by(date=date(2025, 12, 25)).first()
    found_dec = db.query(Event).filter_by(date=date(2025, 12, 26)).first()
    
    # ASSERT - Vérifier qu'ils existent
    assert found_nov is not None
    assert found_dec is not None
    assert found_nov.max_spots ==20
    assert found_nov.confirmed_count ==0
    assert found_dec.max_spots ==2
    assert found_dec.confirmed_count ==0
    assert found_dec.id ==2

    # Après db.commit()
    total_events = db.query(Event).count()
    assert total_events == 2, "Devrait y avoir 2 events dans la DB"


