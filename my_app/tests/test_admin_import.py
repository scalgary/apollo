import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.admin_service import AdminService
from db_models import Admin, User


# ============================================
# FIXTURES POUR ADMIN SERVICE
# ============================================

@pytest.fixture
def admin_service(db):
    """Crée une instance d'AdminService avec la DB de test"""
    return AdminService(db)


@pytest.fixture
def mock_admins_csv(monkeypatch):
    """Mock la fonction load_admins()"""
    
    def mock_load_admins():
        return [
            'admin1@apollo.com',
            'admin2@apollo.com',
            'external.admin@apollo.com'
        ]
    
    # CRITICAL: Patcher là où c'est importé (admin_service), pas où c'est défini (csv_loader)
    from services import admin_service
    monkeypatch.setattr(admin_service, 'load_admins', mock_load_admins)


# ============================================
# TESTS: Import Admins from CSV
# ============================================

def test_import_admins_from_csv_new(admin_service, mock_admins_csv, db):
    """Vérifie l'import de nouveaux admins"""
    # Import
    count = admin_service.import_admins_from_csv()
    
    # Vérifier le count
    assert count == 3
    
    # Vérifier en DB
    admins = db.query(Admin).all()
    assert len(admins) == 3
    
    # Vérifier premier admin
    admin1 = db.query(Admin).filter(Admin.admin_email == 'admin1@apollo.com').first()
    assert admin1 is not None
    assert admin1.user_id is None  # Pas encore lié


def test_import_admins_from_csv_skip_existing(admin_service, mock_admins_csv, db):
    """Vérifie qu'on ne duplique pas les admins existants"""
    # Premier import
    count1 = admin_service.import_admins_from_csv()
    assert count1 == 3
    
    # Deuxième import (devrait skip tous)
    count2 = admin_service.import_admins_from_csv()
    assert count2 == 0
    
    # Vérifier qu'on a toujours 3 admins
    admins = db.query(Admin).all()
    assert len(admins) == 3


def test_import_admins_from_csv_auto_link_user(admin_service, mock_admins_csv, db, full_member_user):
    """Vérifie le link automatique si user existe avec même email"""
    # Modifier l'email du user pour matcher un admin
    full_member_user.email = 'admin1@apollo.com'
    db.commit()
    
    # Import
    count = admin_service.import_admins_from_csv()
    
    # Vérifier que l'admin est lié au user
    admin1 = db.query(Admin).filter(Admin.admin_email == 'admin1@apollo.com').first()
    assert admin1.user_id == full_member_user.id


# ============================================
# TESTS: is_user_admin()
# ============================================

def test_is_user_admin_true(admin_service, db, full_member_user):
    """Vérifie qu'un user admin retourne True"""
    # Créer un admin lié au user
    admin = Admin(
        admin_email='test.admin@apollo.com',
        user_id=full_member_user.id
    )
    db.add(admin)
    db.commit()
    
    result = admin_service.is_user_admin(full_member_user.id)
    assert result is True


def test_is_user_admin_false(admin_service, full_member_user):
    """Vérifie qu'un user non-admin retourne False"""
    result = admin_service.is_user_admin(full_member_user.id)
    assert result is False


def test_is_user_admin_nonexistent_user(admin_service):
    """Vérifie qu'un user_id inexistant retourne False"""
    result = admin_service.is_user_admin(9999)
    assert result is False


# ============================================
# TESTS: is_email_admin()
# ============================================

def test_is_email_admin_true(admin_service, db):
    """Vérifie qu'un email admin retourne True"""
    # Créer un admin
    admin = Admin(admin_email='test.admin@apollo.com')
    db.add(admin)
    db.commit()
    
    result = admin_service.is_email_admin('test.admin@apollo.com')
    assert result is True


def test_is_email_admin_case_insensitive(admin_service, db):
    """Vérifie que la vérification est case-insensitive"""
    # Créer un admin
    admin = Admin(admin_email='test.admin@apollo.com')
    db.add(admin)
    db.commit()
    
    # Tester avec différentes casses
    assert admin_service.is_email_admin('TEST.ADMIN@APOLLO.COM') is True
    assert admin_service.is_email_admin('Test.Admin@Apollo.Com') is True


def test_is_email_admin_false(admin_service):
    """Vérifie qu'un email non-admin retourne False"""
    result = admin_service.is_email_admin('notadmin@test.com')
    assert result is False


# ============================================
# TESTS: get_admin_emails()
# ============================================

def test_get_admin_emails_empty(admin_service):
    """Vérifie une liste vide quand pas d'admins"""
    emails = admin_service.get_admin_emails()
    assert emails == []


def test_get_admin_emails_multiple(admin_service, db):
    """Vérifie la récupération de tous les emails admins"""
    # Créer 3 admins
    admin1 = Admin(admin_email='admin1@apollo.com')
    admin2 = Admin(admin_email='admin2@apollo.com')
    admin3 = Admin(admin_email='admin3@apollo.com')
    
    db.add_all([admin1, admin2, admin3])
    db.commit()
    
    emails = admin_service.get_admin_emails()
    
    assert len(emails) == 3
    assert 'admin1@apollo.com' in emails
    assert 'admin2@apollo.com' in emails
    assert 'admin3@apollo.com' in emails


# ============================================
# TESTS: link_user_to_admin()
# ============================================

def test_link_user_to_admin_success(admin_service, db, full_member_user):
    """Vérifie le lien d'un user à un admin existant"""
    # Créer un admin sans user_id
    admin = Admin(admin_email='test.admin@apollo.com')
    db.add(admin)
    db.commit()
    
    # Lier le user
    success = admin_service.link_user_to_admin(full_member_user.id, 'test.admin@apollo.com')
    
    assert success is True
    
    # Vérifier le lien
    db.refresh(admin)
    assert admin.user_id == full_member_user.id


def test_link_user_to_admin_nonexistent_admin(admin_service, full_member_user):
    """Vérifie qu'on retourne False si admin n'existe pas"""
    success = admin_service.link_user_to_admin(full_member_user.id, 'nonexistent@apollo.com')
    assert success is False


def test_link_user_to_admin_update_existing_link(admin_service, db, full_member_user, punch_card_user):
    """Vérifie qu'on peut changer le user_id d'un admin"""
    # Créer un admin lié au full_member_user
    admin = Admin(
        admin_email='test.admin@apollo.com',
        user_id=full_member_user.id
    )
    db.add(admin)
    db.commit()
    
    # Changer le lien vers punch_card_user
    success = admin_service.link_user_to_admin(punch_card_user.id, 'test.admin@apollo.com')
    
    assert success is True
    
    # Vérifier le nouveau lien
    db.refresh(admin)
    assert admin.user_id == punch_card_user.id