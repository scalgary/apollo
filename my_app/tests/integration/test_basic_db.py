# tests/integration/test_basic_db.py

def test_create_user_in_database(db_session, create_user_apollo):
    """
    Test le plus simple : créer un user et vérifier qu'il est bien en DB
    """
    # Arrange & Act : Créer un user via la fixture
    user = create_user_apollo(
        email="ourson@apollo.com",
        display_name="Ourson",
        real_name="Ourson Real"
    )
    
    # Assert : Vérifier qu'il existe en DB
    from db_models import User
    
    db_user = db_session.query(User).filter_by(email="ourson@apollo.com").first()
    
    assert db_user is not None
    assert db_user.email == "ourson@apollo.com"
    assert db_user.display_name == "Ourson"
    assert db_user.real_name == "Ourson Real"
    assert db_user.id == user.id