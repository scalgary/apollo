import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

# Ajouter le répertoire parent au path pour accéder aux modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.auth_service import AuthService

# ============================================
# FIXTURES POUR AUTH
# ============================================

@pytest.fixture
def auth_service(db):
    """Crée une instance d'AuthService avec la DB de test"""
    return AuthService(db)


@pytest.fixture(autouse=True)
def mock_secret_key(monkeypatch):
    """Override SECRET_KEY pour tous les tests d'auth"""
    monkeypatch.setenv('SECRET_KEY', 'test-secret-key-for-pytest')


# ============================================
# TESTS: Password Management
# ============================================

def test_hash_password(auth_service):
    """Vérifie que hash_password génère un hash bcrypt valide"""
    password = "my_secure_password"
    hashed = auth_service.hash_password(password)
    
    # Vérifications basiques
    assert hashed != password  # Le hash est différent du plaintext
    assert isinstance(hashed, str)
    assert hashed.startswith('$2b$')  # Format bcrypt


def test_verify_password_success(auth_service):
    """Vérifie qu'un bon password est accepté"""
    password = "my_secure_password"
    hashed = auth_service.hash_password(password)
    
    assert auth_service.verify_password(password, hashed) is True


def test_verify_password_failure(auth_service):
    """Vérifie qu'un mauvais password est rejeté"""
    password = "my_secure_password"
    wrong_password = "wrong_password"
    hashed = auth_service.hash_password(password)
    
    assert auth_service.verify_password(wrong_password, hashed) is False


# ============================================
# TESTS: JWT Token Management
# ============================================

def test_create_token(auth_service):
    """Vérifie la création d'un JWT token"""
    user_id = 42
    token = auth_service.create_token(user_id)
    
    assert isinstance(token, str)
    assert len(token) > 0
    # Le token JWT a 3 parties séparées par des points
    assert token.count('.') == 2


def test_decode_token_success(auth_service):
    """Vérifie le décodage d'un token valide"""
    user_id = 42
    token = auth_service.create_token(user_id)
    
    payload = auth_service.decode_token(token)
    
    assert payload['sub'] == str(user_id)
    assert 'exp' in payload


def test_decode_token_invalid(auth_service):
    """Vérifie qu'un token invalide lève une erreur"""
    invalid_token = "this.is.invalid"
    
    with pytest.raises(ValueError, match="Invalid token"):
        auth_service.decode_token(invalid_token)


def test_decode_token_expired(auth_service, monkeypatch):
    """Vérifie qu'un token expiré est rejeté"""
    # Créer un token avec expiration immédiate
    user_id = 42
    
    # Patcher ACCESS_TOKEN_EXPIRE_MINUTES pour créer un token qui expire tout de suite
    from services import auth_service as auth_module
    monkeypatch.setattr(auth_module, 'ACCESS_TOKEN_EXPIRE_MINUTES', -1)
    
    token = auth_service.create_token(user_id)
    
    # Restaurer la valeur normale
    monkeypatch.setattr(auth_module, 'ACCESS_TOKEN_EXPIRE_MINUTES', 60 * 24)
    
    with pytest.raises(ValueError, match="Invalid token"):
        auth_service.decode_token(token)


# ============================================
# TESTS: User Operations
# ============================================

def test_get_user_by_email_exists(auth_service, full_member_user):
    """Vérifie qu'on trouve un user par email"""
    user = auth_service.get_user_by_email(full_member_user.email)
    
    assert user is not None
    assert user.id == full_member_user.id
    assert user.email == full_member_user.email


def test_get_user_by_email_not_exists(auth_service):
    """Vérifie qu'on retourne None si email inexistant"""
    user = auth_service.get_user_by_email("nonexistent@test.com")
    
    assert user is None


def test_get_user_by_id_exists(auth_service, full_member_user):
    """Vérifie qu'on trouve un user par ID"""
    user = auth_service.get_user_by_id(full_member_user.id)
    
    assert user is not None
    assert user.id == full_member_user.id
    assert user.email == full_member_user.email


def test_get_user_by_id_not_exists(auth_service):
    """Vérifie qu'on retourne None si ID inexistant"""
    user = auth_service.get_user_by_id(99999)
    
    assert user is None


# ============================================
# TESTS: Authentication
# ============================================

def test_authenticate_success(auth_service, full_member_user):
    """Vérifie l'authentification avec credentials valides"""
    result = auth_service.authenticate(
        email=full_member_user.email,
        password=full_member_user.plain_password
    )
    
    # Vérifier la structure du résultat
    assert 'access_token' in result
    assert 'token_type' in result
    assert 'user' in result
    
    # Vérifier le token
    assert isinstance(result['access_token'], str)
    assert result['token_type'] == 'bearer'
    
    # Vérifier les infos user
    assert result['user']['id'] == full_member_user.id
    assert result['user']['email'] == full_member_user.email
    assert result['user']['display_name'] == full_member_user.display_name
    assert result['user']['real_name'] == full_member_user.real_name


def test_authenticate_wrong_email(auth_service):
    """Vérifie que l'auth échoue avec email inexistant"""
    with pytest.raises(ValueError, match="Invalid credentials"):
        auth_service.authenticate(
            email="nonexistent@test.com",
            password="anypassword"
        )


def test_authenticate_wrong_password(auth_service, full_member_user):
    """Vérifie que l'auth échoue avec mauvais password"""
    with pytest.raises(ValueError, match="Invalid credentials"):
        auth_service.authenticate(
            email=full_member_user.email,
            password="wrong_password"
        )


# ============================================
# TESTS: Get Current User
# ============================================

def test_get_current_user_success(auth_service, full_member_user):
    """Vérifie qu'on récupère le user depuis un token valide"""
    token = auth_service.create_token(full_member_user.id)
    
    user = auth_service.get_current_user(token)
    
    assert user.id == full_member_user.id
    assert user.email == full_member_user.email


def test_get_current_user_invalid_token(auth_service):
    """Vérifie qu'un token invalide lève une erreur"""
    with pytest.raises(ValueError, match="Invalid token"):
        auth_service.get_current_user("invalid.token.here")


def test_get_current_user_nonexistent_user(auth_service):
    """Vérifie qu'un token valide mais user inexistant lève une erreur"""
    # Créer un token pour un user_id qui n'existe pas
    token = auth_service.create_token(99999)
    
    with pytest.raises(ValueError, match="User not found"):
        auth_service.get_current_user(token)