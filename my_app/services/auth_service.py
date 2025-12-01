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
    
        
    def signup(self, email: str, password: str, display_name: str) -> dict:
        """
        Crée un nouveau compte utilisateur

        Args:
            email: Email de l'utilisateur
            password: Password en clair
            display_name: Nom d'affichage choisi par l'utilisateur

        Returns:
            dict avec user_id et message de succès

        Raises:
            ValueError: Si email pas dans whitelist, déjà utilisé, ou autre erreur
        """
        from utils import load_whitelist
        from db_models import UserEventTypeMembership, EventType

        # 1. Vérifier que l'email est dans la whitelist
        whitelist = load_whitelist()
        email_lower = email.lower().strip()

        if email_lower not in whitelist:
            raise ValueError("Email not authorized. Please contact the administrator.")

        # 2. Vérifier que l'email n'existe pas déjà
        existing_user = self.get_user_by_email(email_lower)
        if existing_user:
            raise ValueError("An account with this email already exists. Please login instead.")

        # 3. Créer le user
        whitelist_data = whitelist[email_lower]
        hashed_password = self.hash_password(password)

        new_user = User(
            email=email_lower,
            hashed_password=hashed_password,
            real_name=whitelist_data['real_name'],
            display_name=display_name.strip()
        )
        self.db.add(new_user)
        self.db.flush()  # Pour obtenir l'ID sans commit complet

        # 4. Créer les memberships depuis la whitelist
        event_types = {et.name: et.id for et in self.db.query(EventType).all()}

        for membership_data in whitelist_data['memberships']:
            event_type_name = membership_data['event_type_name']
            
            if event_type_name not in event_types:
                print(f"Warning: Event type '{event_type_name}' not found, skipping")
                continue
            
            membership_type = membership_data['membership_type']
            total_credits = membership_data['total_credits_purchased']
            
            # Calculer remaining_credits
            if membership_type == 'full_member':
                remaining_credits = None  # Illimité
            else:
                remaining_credits = total_credits if total_credits else 0
            
            membership = UserEventTypeMembership(
                user_id=new_user.id,
                event_type_id=event_types[event_type_name],
                membership_type=membership_type,
                total_credits_purchased=total_credits,
                remaining_credits=remaining_credits
            )
            self.db.add(membership)

        # 5. Commit tout
        self.db.commit()

        return {
            "user_id": new_user.id,
            "message": "Account created successfully"
        }