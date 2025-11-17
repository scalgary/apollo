from db_models import User

def test_signup_success(client, test_user_email, test_password, db):
    """Test inscription avec email whitelisté"""
    response = client.post("/signup", data={
        "email": test_user_email,
        "password": test_password
    }, follow_redirects=False)
    
    assert response.status_code == 302
    assert "/login" in response.headers["location"]
    
    # Vérifier que l'user existe en DB
    user = db.query(User).filter(User.email == test_user_email).first()
    assert user is not None
    assert user.email == test_user_email

def test_login_success(client, test_user_email, test_password):
    """Test connexion réussie"""
    # Créer user
    client.post("/signup", data={
        "email": test_user_email,
        "password": test_password
    })
    
    # Login
    response = client.post("/login", data={
        "email": test_user_email,
        "password": test_password
    }, follow_redirects=False)
    
    assert response.status_code == 302
    assert "access_token" in response.cookies