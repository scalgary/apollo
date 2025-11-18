

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