def test_create_event(db):
    """Test simple: créer un event lié à un event_type"""
    from db_models import Event
    from datetime import date
    
    event = Event(
        event_type_id=1,
        date=date(2025, 12, 25)
        # confirmed_count sera automatiquement 0
    )
    
    db.add(event)
    db.commit()
    db.refresh(event)
    
    assert event.id is not None
    assert event.confirmed_count == 0  # Vérifie que le default fonctionne
    
    print(f"✓ Event créé avec confirmed_count={event.confirmed_count} (default)")