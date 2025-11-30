"""
Tests pour la création et gestion des users avec leurs memberships.
"""

def test_user_with_different_memberships_per_event_type(db):
    """
    Test: Un user peut avoir un membership différent pour chaque event_type.
    
    Scénario:
    - Alice est punch_card avec 5 crédits pour open_play
    - Alice est full_member pour competitive
    """
    from db_models import User, UserEventTypeMembership
    from utils import get_password_hash
    
    # ARRANGE - Créer le user
    user = User(
        email="alice@test.com",
        hashed_password=get_password_hash("password123"),
        real_name="Alice Dupont",
        display_name="Alice"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Créer membership pour open_play (punch_card)
    membership_open = UserEventTypeMembership(
        user_id=user.id,
        event_type_id=1,  # open_play
        membership_type='punch_card',
        total_credits_purchased=5
    )
    db.add(membership_open)
    
    # Créer membership pour competitive (full_member)
    membership_competitive = UserEventTypeMembership(
        user_id=user.id,
        event_type_id=2,  # competitive
        membership_type='full_member',
        total_credits_purchased=None
    )
    db.add(membership_competitive)
    db.commit()
    
    # ACT - Récupérer les memberships depuis la DB
    memberships = db.query(UserEventTypeMembership).filter_by(
        user_id=user.id
    ).all()
    
    # ASSERT - Vérifier qu'on a bien 2 memberships
    assert len(memberships) == 2, "Alice devrait avoir 2 memberships"
    
    # Vérifier le membership open_play
    open_membership = db.query(UserEventTypeMembership).filter_by(
        user_id=user.id,
        event_type_id=1
    ).first()
    assert open_membership is not None
    assert open_membership.membership_type == 'punch_card'
    assert open_membership.total_credits_purchased == 5
    
    # Vérifier le membership competitive
    competitive_membership = db.query(UserEventTypeMembership).filter_by(
        user_id=user.id,
        event_type_id=2
    ).first()
    assert competitive_membership is not None
    assert competitive_membership.membership_type == 'full_member'
    assert competitive_membership.total_credits_purchased is None
    
    print(f"✓ Alice a bien 2 memberships différents:")
    print(f"  - open_play: punch_card (5 crédits)")
    print(f"  - competitive: full_member")


def test_query_user_memberships(db):
    """
    Test: Récupérer tous les memberships d'un user avec une seule requête.
    """
    from db_models import User, UserEventTypeMembership, EventType
    from utils import get_password_hash
    
    # ARRANGE - Créer Bob avec 2 memberships
    bob = User(
        email="bob@test.com",
        hashed_password=get_password_hash("password123"),
        real_name="Bob Martin",
        display_name="Bob"
    )
    db.add(bob)
    db.commit()
    db.refresh(bob)
    
    # Bob: punch_card pour les 2 types
    for event_type_id, credits in [(1, 3), (2, 8)]:
        membership = UserEventTypeMembership(
            user_id=bob.id,
            event_type_id=event_type_id,
            membership_type='punch_card',
            total_credits_purchased=credits
        )
        db.add(membership)
    db.commit()
    
    # ACT - Récupérer les memberships avec les noms des event_types
    memberships = db.query(
        UserEventTypeMembership, EventType
    ).join(
        EventType, UserEventTypeMembership.event_type_id == EventType.id
    ).filter(
        UserEventTypeMembership.user_id == bob.id
    ).all()
    
    # ASSERT
    assert len(memberships) == 2
    
    # Vérifier les détails
    for membership, event_type in memberships:
        assert membership.user_id == bob.id
        assert membership.membership_type == 'punch_card'
        
        if event_type.name == 'open_play':
            assert membership.total_credits_purchased == 3
        elif event_type.name == 'competitive':
            assert membership.total_credits_purchased == 8
    
    print(f"✓ Bob a {len(memberships)} memberships, tous punch_card")


def test_user_can_have_only_one_membership_per_event_type(db):
    """
    Test: Un user ne peut pas avoir 2 memberships pour le même event_type.
    La contrainte UNIQUE devrait l'empêcher.
    """
    from db_models import User, UserEventTypeMembership
    from utils import get_password_hash
    from sqlalchemy.exc import IntegrityError
    
    # ARRANGE
    user = User(
        email="charlie@test.com",
        hashed_password=get_password_hash("password123"),
        real_name="Charlie",
        display_name="Charlie"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Premier membership pour open_play
    membership1 = UserEventTypeMembership(
        user_id=user.id,
        event_type_id=1,
        membership_type='full_member',
        total_credits_purchased=None
    )
    db.add(membership1)
    db.commit()
    
    # ACT & ASSERT - Essayer d'ajouter un 2e membership pour open_play
    membership2 = UserEventTypeMembership(
        user_id=user.id,
        event_type_id=1,  # Même event_type!
        membership_type='punch_card',
        total_credits_purchased=5
    )
    db.add(membership2)
    
    # Ça devrait échouer avec IntegrityError
    try:
        db.commit()
        assert False, "Devrait avoir levé une IntegrityError"
    except IntegrityError:
        db.rollback()
        print("✓ Impossible d'avoir 2 memberships pour le même event_type (contrainte respectée)")

def test_user_with_only_one_membership(db):
    """
    Test: Un user peut n'avoir qu'un seul membership.
    Dans la DB, s'il n'existe pas, il n'y a pas de "défaut".
    """
    from db_models import User, UserEventTypeMembership
    from utils import get_password_hash
    
    # ARRANGE - Créer David avec seulement open_play
    david = User(
        email="david@test.com",
        hashed_password=get_password_hash("password123"),
        real_name="David",
        display_name="David"
    )
    db.add(david)
    db.commit()
    db.refresh(david)
    
    # Créer membership SEULEMENT pour open_play
    membership_open = UserEventTypeMembership(
        user_id=david.id,
        event_type_id=1,
        membership_type='full_member',
        total_credits_purchased=None
    )
    db.add(membership_open)
    db.commit()
    
    # ACT - Chercher tous ses memberships
    memberships = db.query(UserEventTypeMembership).filter_by(
        user_id=david.id
    ).all()
    
    # ASSERT - Il a seulement 1 membership
    assert len(memberships) == 1
    assert memberships[0].event_type_id == 1
    
    # Vérifier qu'il n'a PAS de membership pour competitive
    competitive_membership = db.query(UserEventTypeMembership).filter_by(
        user_id=david.id,
        event_type_id=2
    ).first()
    
    assert competitive_membership is None, "David ne devrait pas avoir de membership pour competitive"
    
    print("✓ David a seulement 1 membership (open_play)")
    print("✓ Pas de membership competitive dans la DB")

def test_get_user_membership_with_default(db):
    """
    Test: Fonction qui retourne le membership, ou un défaut si absent.
    Simule la logique applicative de sécurité.
    """
    from db_models import User, UserEventTypeMembership
    from utils import get_password_hash
    
    def get_user_membership_for_event_type(db, user_id, event_type_id):
        """
        Récupère le membership d'un user pour un event_type.
        Si absent, retourne un défaut sécurisé (punch_card, 0 crédits).
        """
        membership = db.query(UserEventTypeMembership).filter_by(
            user_id=user_id,
            event_type_id=event_type_id
        ).first()
        
        if membership:
            return {
                'membership_type': membership.membership_type,
                'total_credits_purchased': membership.total_credits_purchased
            }
        else:
            # DÉFAUT DE SÉCURITÉ
            return {
                'membership_type': 'punch_card',
                'total_credits_purchased': 0
            }
    
    # ARRANGE - Créer Emma avec seulement open_play
    emma = User(
        email="emma@test.com",
        hashed_password=get_password_hash("password123"),
        real_name="Emma",
        display_name="Emma"
    )
    db.add(emma)
    db.commit()
    db.refresh(emma)
    
    membership_open = UserEventTypeMembership(
        user_id=emma.id,
        event_type_id=1,
        membership_type='full_member',
        total_credits_purchased=None
    )
    db.add(membership_open)
    db.commit()
    
    # ACT - Récupérer les memberships via la fonction
    open_membership = get_user_membership_for_event_type(db, emma.id, 1)
    competitive_membership = get_user_membership_for_event_type(db, emma.id, 2)
    
    # ASSERT
    # open_play: existe en DB
    assert open_membership['membership_type'] == 'full_member'
    assert open_membership['total_credits_purchased'] is None
    
    # competitive: n'existe pas en DB, retourne le défaut
    assert competitive_membership['membership_type'] == 'punch_card'
    assert competitive_membership['total_credits_purchased'] == 0
    
    print("✓ open_play: full_member (depuis DB)")
    print("✓ competitive: punch_card 0 crédits (défaut de sécurité)")