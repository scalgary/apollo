import pytest
from datetime import datetime, timedelta, date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.event_service import EventService
from db_models import Event, EventType, Attendee


# ============================================
# FIXTURES POUR EVENT SERVICE
# ============================================

@pytest.fixture
def event_service(db):
    """Crée une instance d'EventService avec la DB de test"""
    return EventService(db)

@pytest.fixture
def mock_csv_files(monkeypatch):
    """Mock les fonctions load_events et load_event_types"""
    
    def mock_load_event_types():
        return [
            {
                'name': 'test_open_play',
                'display_name': 'Test Indoor',
                'default_location': 'Test Arena',
                'default_time_start': '19:00',
                'default_time_end': '21:00',
                'default_max_capacity': 20,
                'color': '#4A90E2'
            },
            {
                'name': 'test_competitive',
                'display_name': 'Test Outdoor',
                'default_location': 'Test Park',
                'default_time_start': '14:00',
                'default_time_end': '16:00',
                'default_max_capacity': 16,
                'color': '#7ED321'
            }
        ]
    
    def mock_load_events():
        future_date_1 = (date.today() + timedelta(days=10)).strftime('%Y-%m-%d')
        future_date_2 = (date.today() + timedelta(days=17)).strftime('%Y-%m-%d')
        future_date_3 = (date.today() + timedelta(days=15)).strftime('%Y-%m-%d')
        
        return [
            {'event_type_name': 'test_open_play', 'date': future_date_1},
            {'event_type_name': 'test_open_play', 'date': future_date_2},
            {'event_type_name': 'test_competitive', 'date': future_date_3}
        ]
    
    # CRITICAL: Patcher là où les fonctions sont IMPORTÉES, pas où elles sont définies
    from services import event_service
    monkeypatch.setattr(event_service, 'load_event_types', mock_load_event_types)
    monkeypatch.setattr(event_service, 'load_events', mock_load_events)



# ============================================
# TESTS: Import Event Types from CSV
# ============================================

def test_import_event_types_from_csv_new(event_service, mock_csv_files, db):
    """Vérifie l'import de nouveaux event types"""
    # Import
    count = event_service.import_event_types_from_csv()
    
    # Vérifier le count (2 nouveaux + 2 existants dans fixture db)
    assert count == 2
    
    # Vérifier en DB
    test_open_play = db.query(EventType).filter(
        EventType.name == 'test_open_play'
    ).first()
    
    assert test_open_play is not None
    assert test_open_play.display_name == 'Test Indoor'
    assert test_open_play.default_max_capacity == 20


def test_import_event_types_from_csv_update_existing(event_service, mock_csv_files, db):
    """Vérifie la mise à jour d'event types existants"""
    # Créer un event type existant avec anciennes valeurs
    existing = EventType(
        name='test_open_play',
        display_name='Old Name',
        default_location='Old Location',
        default_time_start='18:00',
        default_time_end='20:00',
        default_max_capacity=10,
        color='#000000'
    )
    db.add(existing)
    db.commit()
    
    # Import (devrait update)
    count = event_service.import_event_types_from_csv()
    
    # Vérifier que ça n'a pas créé de nouveau (count = 1 pour test_competitive)
    assert count == 1
    
    # Vérifier la mise à jour
    db.refresh(existing)
    assert existing.display_name == 'Test Indoor'
    assert existing.default_location == 'Test Arena'
    assert existing.default_max_capacity == 20


# ============================================
# TESTS: Import Events from CSV
# ============================================

def test_import_events_from_csv_new(event_service, mock_csv_files, db):
    """Vérifie l'import de nouveaux events"""
    # D'abord importer les event types
    event_service.import_event_types_from_csv()
    
    # Ensuite importer les events
    count = event_service.import_events_from_csv()
    
    assert count == 3
    
    # Vérifier en DB
    events = db.query(Event).all()
    # 3 nouveaux events
    assert len(events) >= 3


def test_import_events_from_csv_skip_existing(event_service, mock_csv_files, db):
    """Vérifie qu'on ne duplique pas les events existants"""
    # Importer event types
    event_service.import_event_types_from_csv()
    
    # Premier import
    count1 = event_service.import_events_from_csv()
    assert count1 == 3
    
    # Deuxième import (devrait skip tous)
    count2 = event_service.import_events_from_csv()
    assert count2 == 0
    
    # Vérifier qu'on a toujours 3 events
    events = db.query(Event).all()
    assert len(events) == 3




def test_import_events_from_csv_missing_event_type(event_service, db, monkeypatch):
    """Vérifie qu'on skip les events avec event_type inexistant"""
    
    def mock_load_events_invalid():
        return [
            {'event_type_name': 'nonexistent_type', 'date': '2025-12-10'}
        ]
    
    # CRITICAL: Mocker là où c'est importé (event_service), pas où c'est défini (csv_loader)
    from services import event_service as event_service_module
    monkeypatch.setattr(event_service_module, 'load_events', mock_load_events_invalid)
    
    count = event_service.import_events_from_csv()
    
    assert count == 0


# ============================================
# TESTS: Get All Events With User Status
# ============================================

def test_get_all_events_with_user_status_no_registration(event_service, full_member_user, test_event):
    """Vérifie la récupération d'events sans inscription"""
    events = event_service.get_all_events_with_user_status(full_member_user.id)
    
    assert len(events) >= 1
    
    event = events[0]
    assert event['id'] == test_event.id
    assert event['user_status'] is None
    assert event['confirmed_count'] == 0
    assert event['waitlist_count'] == 0


def test_get_all_events_with_user_status_confirmed(
    event_service, full_member_user, test_event, create_attendee
):
    """Vérifie le statut confirmed dans la liste"""
    # Inscrire le user
    create_attendee(test_event, full_member_user, status='confirmed')
    
    events = event_service.get_all_events_with_user_status(full_member_user.id)
    
    event = events[0]
    assert event['user_status'] == 'confirmed'


def test_get_all_events_with_user_status_waiting(
    event_service, full_member_user, test_event, create_attendee
):
    """Vérifie le statut waiting dans la liste"""
    # Mettre le user en waitlist
    create_attendee(test_event, full_member_user, status='waiting')
    
    events = event_service.get_all_events_with_user_status(full_member_user.id)
    
    event = events[0]
    assert event['user_status'] == 'waiting'


def test_get_all_events_with_user_status_counts(
    event_service, db, full_member_user, punch_card_user, test_event, create_attendee, create_user
):
    """Vérifie les counts (confirmed + waitlist)"""
    # Créer 2 users supplémentaires
    user3 = create_user(email="user3@test.com")
    user4 = create_user(email="user4@test.com")
    
    # 2 confirmed
    create_attendee(test_event, full_member_user, status='confirmed')
    create_attendee(test_event, punch_card_user, status='confirmed')
    
    # 2 waiting
    create_attendee(test_event, user3, status='waiting')
    create_attendee(test_event, user4, status='waiting')
    
    # Update confirmed_count
    test_event.confirmed_count = 2
    db.commit()
    
    events = event_service.get_all_events_with_user_status(full_member_user.id)
    
    event = events[0]
    assert event['confirmed_count'] == 2
    assert event['waitlist_count'] == 2
    assert event['available_spots'] == 18  # 20 - 2


def test_get_all_events_only_future(event_service, db, full_member_user, create_event):
    """Vérifie qu'on ne récupère que les events futurs"""
    # Event passé
    past_event = create_event(days_from_now=-7)
    
    # Event futur
    future_event = create_event(days_from_now=7)
    
    events = event_service.get_all_events_with_user_status(full_member_user.id)
    
    # Ne devrait contenir que le futur
    event_ids = [e['id'] for e in events]
    assert future_event.id in event_ids
    assert past_event.id not in event_ids


# ============================================
# TESTS: Get Events For Schedule
# ============================================

def test_get_events_for_schedule_formatting(event_service, full_member_user, test_event):
    """Vérifie le formatage des dates pour la page schedule"""
    events = event_service.get_events_for_schedule(full_member_user.id)
    
    event = events[0]
    
    # Vérifier les champs formatés
    assert 'month' in event
    assert 'day' in event
    assert 'weekday' in event
    
    # Vérifier le format
    assert len(event['month']) == 3  # ex: "Dec"
    assert event['day'].isdigit()    # ex: "10"
    assert len(event['weekday']) == 3  # ex: "Mon"


# ============================================
# TESTS: Get Waitlist Users
# ============================================

def test_get_waitlist_users_empty(event_service, test_event):
    """Vérifie une waitlist vide"""
    waitlist = event_service.get_waitlist_users(test_event.id)
    
    assert waitlist == []


def test_get_waitlist_users_ordered(
    event_service, test_event, full_member_user, punch_card_user, create_attendee, create_user
):
    """Vérifie l'ordre de la waitlist (FIFO)"""
    user3 = create_user(email="user3@test.com")
    
    # Inscrire dans l'ordre
    attendee1 = create_attendee(test_event, full_member_user, status='waiting')
    attendee2 = create_attendee(test_event, punch_card_user, status='waiting')
    attendee3 = create_attendee(test_event, user3, status='waiting')
    
    waitlist = event_service.get_waitlist_users(test_event.id)
    
    assert len(waitlist) == 3
    
    # Vérifier l'ordre et les positions
    assert waitlist[0]['position'] == 1
    assert waitlist[0]['email'] == full_member_user.email
    
    assert waitlist[1]['position'] == 2
    assert waitlist[1]['email'] == punch_card_user.email
    
    assert waitlist[2]['position'] == 3
    assert waitlist[2]['email'] == user3.email


def test_get_waitlist_users_exclude_confirmed(
    event_service, test_event, full_member_user, punch_card_user, create_attendee
):
    """Vérifie qu'on n'inclut pas les confirmed dans la waitlist"""
    # 1 confirmed
    create_attendee(test_event, full_member_user, status='confirmed')
    
    # 1 waiting
    create_attendee(test_event, punch_card_user, status='waiting')
    
    waitlist = event_service.get_waitlist_users(test_event.id)
    
    # Seulement le waiting
    assert len(waitlist) == 1
    assert waitlist[0]['email'] == punch_card_user.email


def test_import_events_from_csv_missing_event_type(event_service, db, monkeypatch):
    """Vérifie qu'on skip les events avec event_type inexistant"""
    
    def mock_load_events_invalid():
        return [
            {'event_type_name': 'nonexistent_type', 'date': '2025-12-10'}
        ]
    
    # CRITICAL: Mocker là où c'est importé (event_service), pas où c'est défini (csv_loader)
    from services import event_service as event_service_module
    monkeypatch.setattr(event_service_module, 'load_events', mock_load_events_invalid)
    
    count = event_service.import_events_from_csv()
    
    assert count == 0