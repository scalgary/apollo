

conftest.py
├── Fixtures d'Infrastructure
│   ├── db              → Crée/détruit la DB pour chaque test
│   ├── client          → TestClient pour simuler HTTP
│   └── setup_test_whitelist → Mock les CSV
│
├── Fixtures de Données
│   ├── full_member_user → User précréé
│   ├── punch_card_user  → User précréé
│   └── test_event       → Event précréé
│
└── Fixtures Utilitaires
    ├── test_user_email  → Email par défaut
    ├── test_password    → Password par défaut
    └── mock_auth        → Simule l'authentification


# Installer pytest
pip install pytest pytest-cov

# Lancer tous les tests
pytest

# Avec coverage
pytest --cov=app tests/

# Un fichier spécifique
pytest tests/test_auth.py

# Un test spécifique
pytest tests/test_auth.py::test_login_success

# Mode verbose
pytest -v

docker exec apollo-app pytest tests  -v -s

docker exec apollo-app pytest tests/test_users.py
docker-compose down -v  

docker-compose -f docker-compose.yml up

#remove all the process
docker rm $(docker ps -aq)