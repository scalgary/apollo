# tests/test_users.py

def test_create_full_member_user(db):
    """
    Test simple: créer un full member et vérifier ses attributs
    """
    from db_models import User
    
    # ARRANGE - Préparer les données
    email = "fullmember@test.com"
    password_hash = "fake_hash_for_now"
    
    # ACT - Créer le user
    user = User(
        email=email,
        hashed_password=password_hash,
        real_name = "User fullmember",
        display_name = "User F",
        membership_type='full_member',
        initial_credits=None,
        remaining_credits=None
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)  # Recharge les données depuis la DB (pour avoir l'id)
    
    # ASSERT - Vérifier
    assert user.id is not None, "Le user devrait avoir un ID après commit"
    assert user.email == email
    assert user.membership_type == 'full_member'
    assert user.initial_credits is None, "Full member n'a pas de limite de crédits"
    assert user.remaining_credits is None, "Full member n'a pas de crédits à décrémenter"
    
    print(f"✓ User créé avec l'ID: {user.id}")


def test_create_punch_card_user(db):
    """
    Test simple: créer un punch card user et vérifier ses attributs
    """
    from db_models import User
    
    # ARRANGE
    email = "punchcard@test.com"
    password_hash = "fake_hash_for_now"
    
    # ACT
    user = User(
        email=email,
        hashed_password=password_hash,
        real_name = "Punchcard",
        display_name = "Punchcard",
        membership_type='punch_card',
        initial_credits=10,      # Capacité totale
        remaining_credits=10     # Ce qui reste (au début = total)
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # ASSERT
    assert user.id is not None
    assert user.email == email
    assert user.membership_type == 'punch_card'
    assert user.initial_credits == 10, "Le forfait devrait être de 10 crédits"
    assert user.remaining_credits == 10, "Au début, tous les crédits sont disponibles"
    
    print(f"✓ Punch card user créé avec {user.remaining_credits}/{user.initial_credits} crédits")


def test_query_users_from_db(db):
    """
    Test: Créer 2 users et vérifier qu'on peut les retrouver
    """
    from db_models import User
    
    # ARRANGE - Créer 2 users
    full_member = User(
        email="full@test.com",
        hashed_password="hash1",
        real_name = "User fullmember",
        display_name = "User F",
        membership_type='full_member',
        initial_credits=None,
        remaining_credits=None
    )
    
    punch_card = User(
        email="punch@test.com",
        hashed_password="hash2",
        real_name = "Punchcard",
        display_name = "Punchcard",
        membership_type='punch_card',
        initial_credits=5,
        remaining_credits=3  # A déjà utilisé 2 crédits
    )
    
    db.add(full_member)
    db.add(punch_card)
    db.commit()
    
    # ACT - Les retrouver via des requêtes
    found_full = db.query(User).filter_by(email="full@test.com").first()
    found_punch = db.query(User).filter_by(email="punch@test.com").first()
    
    # ASSERT - Vérifier qu'ils existent
    assert found_full is not None
    assert found_full.membership_type == 'full_member'
    
    assert found_punch is not None  
    assert found_punch.membership_type == 'punch_card'
    assert found_punch.remaining_credits == 3
    
    # BONUS - Compter tous les users
    total_users = db.query(User).count()
    assert total_users == 2, "Devrait y avoir exactement 2 users"
    
    print(f"✓ Retrouvé {total_users} users dans la DB")

def test_full_and_punch_together(full_member_user, punch_card_user, db):
    from db_models import User

    """Test avec les deux types d'users"""
    
    # Les deux users sont automatiquement créés par les fixtures
    assert full_member_user.membership_type == "full_member"
    assert full_member_user.email == "fullmember@test.com"
    assert full_member_user.remaining_credits is None
    
    assert punch_card_user.membership_type == "punch_card"
    assert punch_card_user.email == "punchcard@test.com"
    assert punch_card_user.remaining_credits == 3
    
    # Tu as 2 users dans la DB
    assert db.query(User).count() == 2
    
    # Maintenant fais tes tests avec ces deux users
    # Par exemple: tester l'inscription aux événements

def test_db_is_empty_at_start(db):
    """
    Test: Vérifier que chaque test démarre avec une DB vide
    """
    from db_models import User
    
    # Au début du test, la DB devrait être vide
    user_count = db.query(User).count()
    
    assert user_count == 0, "La DB devrait être vide au début de chaque test"
    
    print("✓ Confirmation: DB vide au démarrage du test")