# backend/services/auth_service.py
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from db_models import User
from utils import load_whitelist
from fastapi import HTTPException

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def __init__(self, db: Session):
        self.db = db
    
    def register_user(self, email: str, password: str, name: str):
        whitelist = load_whitelist()
        
        # Vérifier si l'email est dans la whitelist (dict maintenant)
        if email not in whitelist:
            raise HTTPException(
                status_code=403,
                detail="Email not authorized"
            )
        
        # Check if already exists
        existing = self.db.query(User).filter(User.email == email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Récupérer les infos de membership depuis la whitelist
        user_info = whitelist[email]
        
        # Create user
        hashed_pw = pwd_context.hash(password)
        user = User(
            email=email,
            hashed_password=hashed_pw  # ← Attention: ton modèle utilise "hashed_password" pas "password_hash"
     
        )
        self.db.add(user)
        self.db.commit()
        
        return user