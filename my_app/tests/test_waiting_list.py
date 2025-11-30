import pytest
from datetime import date, datetime, timedelta



def test_waitlist_promotion_priority(db, create_user):
    from db_models import Event, Attendee, UserEventTypeMembership
    """Test la priorité de promotion de la waitlist selon les 7 jours"""
    
    # 1. Créer un événement dans 10 jours, complet (2 places seulement)
    event_date = date.today() + timedelta(days=10)
    event = Event(
        event_type_id=1,  # open_play
        date=event_date,
        confirmed_count=2  # Complet
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    
    # 2. Créer 4 users avec memberships
    punch1 = create_user(
        email="punch1@test.com",
        membership_type="punch_card",
        total_credits=10
    )
    
    full1 = create_user(
        email="full1@test.com",
        membership_type="full_member"
    )
    
    punch2 = create_user(
        email="punch2@test.com",
        membership_type="punch_card",
        total_credits=10
    )
    
    full2 = create_user(
        email="full2@test.com",
        membership_type="full_member"
    )
    
    # 3. Créer des inscriptions en waitlist avec différentes dates
    # punch1: inscrit il y a 10 jours (>7 jours avant event)
    attendee1 = Attendee(
        user_id=punch1.id,
        event_id=event.id,
        status='waiting',
        registered_at=datetime.now() - timedelta(days=10)
    )
    
    # full1: inscrit il y a 8 jours (>7 jours avant event)
    attendee2 = Attendee(
        user_id=full1.id,
        event_id=event.id,
        status='waiting',
        registered_at=datetime.now() - timedelta(days=8)
    )
    
    # punch2: inscrit il y a 2 jours (<7 jours avant event)
    attendee3 = Attendee(
        user_id=punch2.id,
        event_id=event.id,
        status='waiting',
        registered_at=datetime.now() - timedelta(days=2)
    )
    
    # full2: inscrit il y a 1 jour (<7 jours avant event)
    attendee4 = Attendee(
        user_id=full2.id,
        event_id=event.id,
        status='waiting',
        registered_at=datetime.now() - timedelta(days=1)
    )
    
    db.add_all([attendee1, attendee2, attendee3, attendee4])
    db.commit()
    
    print("\n" + "="*60)
    print("TEST: Ordre de promotion waitlist")
    print("="*60)
    print(f"\nEvent date: {event_date}")
    print(f"Event confirmé: {event.confirmed_count}/2")
    
    print("\nWaitlist actuelle (ordre d'inscription):")
    print("1. punch1@test.com - inscrit il y a 10 jours")
    print("2. full1@test.com - inscrit il y a 8 jours")
    print("3. punch2@test.com - inscrit il y a 2 jours")
    print("4. full2@test.com - inscrit il y a 1 jour")
    
    print("\n⚠️ ORDRE ATTENDU DE PROMOTION:")
    print("1. full1@test.com (full_member, >7 jours) ← PRIORITAIRE")
    print("2. punch1@test.com (punch_card, >7 jours)")
    print("3. punch2@test.com (inscrit avant full2, <7 jours)")
    print("4. full2@test.com")
    
    # 4. Simuler la logique de promotion (copié depuis update_status)
    waiting_list = db.query(Attendee, UserEventTypeMembership).join(
        UserEventTypeMembership, 
        (Attendee.user_id == UserEventTypeMembership.user_id) & 
        (UserEventTypeMembership.event_type_id == event.event_type_id)
    ).filter(
        Attendee.event_id == event.id,
        Attendee.status == 'waiting'
    ).all()
    
    early_registrations = []
    late_registrations = []
    
    for attendee_obj, membership_obj in waiting_list:
        days_before_event = (event.date - attendee_obj.registered_at.date()).days
        
        if days_before_event > 7:
            early_registrations.append((attendee_obj, membership_obj))
        else:
            late_registrations.append((attendee_obj, membership_obj))
    
    # Trier early: full_member d'abord
    early_registrations.sort(
        key=lambda x: (
            0 if x[1].membership_type == 'full_member' else 1,
            x[0].registered_at
        )
    )
    
    # Trier late: par date seulement
    late_registrations.sort(key=lambda x: x[0].registered_at)
    
    sorted_waiting = early_registrations + late_registrations
    
    print("\n✅ ORDRE CALCULÉ PAR LA LOGIQUE:")
    for i, (att, mem) in enumerate(sorted_waiting, 1):
        user = db.query(User).filter(User.id == att.user_id).first()
        print(f"{i}. {user.email} ({mem.membership_type})")
    
    # 5. Vérifications
    from db_models import User
    first_user = db.query(User).filter(User.id == sorted_waiting[0][0].user_id).first()
    assert first_user.email == "full1@test.com", "Le premier doit être full1 (full_member, >7 jours)"
    
    second_user = db.query(User).filter(User.id == sorted_waiting[1][0].user_id).first()
    assert second_user.email == "punch1@test.com", "Le deuxième doit être punch1 (punch_card, >7 jours)"
    
    third_user = db.query(User).filter(User.id == sorted_waiting[2][0].user_id).first()
    assert third_user.email == "punch2@test.com", "Le troisième doit être punch2 (inscrit avant full2)"
    
    print("\n✓ Test passé! L'ordre de promotion est correct.")
    print("="*60)