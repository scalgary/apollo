from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
import bcrypt
from sqlalchemy.orm import Session
from db_models import User
import os

SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


class AuthService:
    """Service pour gérer l'authentification et les tokens JWT"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # === Password Management ===
    
    def hash_password(self, password: str) -> str:
        """Hash un password avec bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Vérifie si le password correspond au hash"""
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    # === JWT Token Management ===
    
    def create_token(self, user_id: int) -> str:
        """Génère un JWT token pour un user_id"""
        payload = {
            "sub": str(user_id),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    def decode_token(self, token: str) -> dict:
        """Décode et valide un JWT token, retourne le payload"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError as e:
            raise ValueError(f"Invalid token: {str(e)}")
    
    # === User Operations ===
    
    def get_user_by_email(self, email: str) -> User | None:
        """Récupère un user par email"""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_user_by_id(self, user_id: int) -> User | None:
        """Récupère un user par ID"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    # === Authentication ===
    
    def authenticate(self, email: str, password: str) -> dict:
        """
        Vérifie les credentials et retourne token + user info
        
        Raises:
            ValueError: Si email ou password invalide
        """
        # 1. Chercher user
        user = self.get_user_by_email(email)
        if not user:
            raise ValueError("Invalid credentials")
        
        # 2. Vérifier password
        if not self.verify_password(password, user.hashed_password):
            raise ValueError("Invalid credentials")
        
        # 3. Générer token
        token = self.create_token(user.id)
        
        # 4. Retourner résultat
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "display_name": user.display_name,
                "real_name": user.real_name
            }
        }
    
    def get_current_user(self, token: str) -> User:
        """
        Récupère le user depuis un JWT token
        
        Raises:
            ValueError: Si token invalide ou user non trouvé
        """
        payload = self.decode_token(token)
        user_id_str = payload.get("sub")
        
        if not user_id_str:
            raise ValueError("Invalid token: missing user_id")
        
        user = self.get_user_by_id(int(user_id_str))
        if not user:
            raise ValueError("User not found")
        
        return user