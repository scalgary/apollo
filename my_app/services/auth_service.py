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
            ValueError: Si email pas autorisé, déjà utilisé, ou autre erreur
        """
        from db_models import UserEventTypeMembership, EventType, Friend
        import os

        email_lower = email.lower().strip()

        # 1. Vérifier que l'email n'est pas un admin
        # Option 1: ENV vars
        admin_emails_env = []
        for i in range(1, 3):
            admin_email = os.getenv(f'ADMIN_EMAIL_{i}')
            if admin_email:
                admin_emails_env.append(admin_email.strip().lower())
        
        # Option 2: CSV
        from utils import load_admins
        admins_list = load_admins()
        admin_emails_csv = [admin['admin_email'] for admin in admins_list]
        
        # Combiner les deux sources
        all_admin_emails = set(admin_emails_env + admin_emails_csv)

        if email_lower in all_admin_emails:
            raise ValueError("Admin accounts cannot signup manually. Contact administrator.")

        # 2. Vérifier que l'email est autorisé
        # Option 1: Friends table (priorité)
        friends = self.db.query(Friend).filter(Friend.email == email_lower).all()
        
 
        real_name = friends[0].real_name
        memberships_source = 'db'

        # 3. Vérifier que l'email n'existe pas déjà
        existing_user = self.get_user_by_email(email_lower)
        if existing_user:
            raise ValueError("An account with this email already exists. Please login instead.")

        # 4. Créer le user
        hashed_password = self.hash_password(password)

        new_user = User(
            email=email_lower,
            hashed_password=hashed_password,
            real_name=real_name,
            display_name=display_name.strip()
        )
        self.db.add(new_user)
        self.db.flush()

        # 5. Récupérer TOUS les event types
        all_event_types = self.db.query(EventType).all()
        event_types_dict_by_id = {et.id: et for et in all_event_types}
        event_types_dict_by_name = {et.event_type_name: et.id for et in all_event_types}

        # 6. Créer memberships selon la source
        created_event_type_ids = set()
        
        if memberships_source == 'db':
            # Source: Friends table
            for friend in friends:
                created_event_type_ids.add(friend.event_type_id)
                
                if friend.membership_type == 'full_member':
                    remaining_credits = None
                else:
                    # IMPORTANT: Copier les crédits de Friends
                    remaining_credits = friend.total_credits_purchased if friend.total_credits_purchased else 0
                
                membership = UserEventTypeMembership(
                    user_id=new_user.id,
                    event_type_id=friend.event_type_id,
                    membership_type=friend.membership_type,
                    total_credits_purchased=friend.total_credits_purchased,  # Copier aussi total
                    remaining_credits=remaining_credits
                )
                self.db.add(membership)
        else:
            # Source: CSV
            for membership_data in csv_memberships:
                event_type_name = membership_data['event_type_name']
                
                if event_type_name not in event_types_dict_by_name:
                    print(f"Warning: Event type '{event_type_name}' not found, skipping")
                    continue
                
                event_type_id = event_types_dict_by_name[event_type_name]
                created_event_type_ids.add(event_type_id)
                
                membership_type = membership_data['membership_type']
                total_credits = membership_data['total_credits_purchased']
                
                if membership_type == 'full_member':
                    remaining_credits = None
                else:
                    remaining_credits = total_credits if total_credits else 0
                
                membership = UserEventTypeMembership(
                    user_id=new_user.id,
                    event_type_id=event_type_id,
                    membership_type=membership_type,
                    total_credits_purchased=total_credits,
                    remaining_credits=remaining_credits
                )
                self.db.add(membership)

        # 7. AUTO-CRÉER punch_card 0 pour event types manquants
        all_event_type_ids = set(event_types_dict_by_id.keys())
        missing_event_type_ids = all_event_type_ids - created_event_type_ids
        
        for event_type_id in missing_event_type_ids:
            membership = UserEventTypeMembership(
                user_id=new_user.id,
                event_type_id=event_type_id,
                membership_type='punch_card',
                total_credits_purchased=0,
                remaining_credits=0
            )
            self.db.add(membership)

        # 8. Commit tout
        self.db.commit()

        return {
            "user_id": new_user.id,
            "message": "Account created successfully"
        }     
  # === Password Reset ===

    def create_reset_token(self, email: str) -> str:
        """
        Génère un token JWT pour reset password (expire en 1h)
        
        Args:
            email: Email de l'utilisateur
        
        Returns:
            str: Token JWT
        
        Raises:
            ValueError: Si user n'existe pas
        """
        user = self.get_user_by_email(email)
        if not user:
            raise ValueError("No account found with this email")
        
        payload = {
            "sub": str(user.id),
            "purpose": "password_reset",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)  # Expire en 1h
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


    def verify_reset_token(self, token: str) -> int:
        """
        Vérifie et décode un token de reset password
        
        Args:
            token: Token JWT
        
        Returns:
            int: user_id
        
        Raises:
            ValueError: Si token invalide ou expiré
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # Vérifier que c'est bien un token de reset
            if payload.get("purpose") != "password_reset":
                raise ValueError("Invalid reset token")
            
            user_id_str = payload.get("sub")
            if not user_id_str:
                raise ValueError("Invalid reset token")
            
            return int(user_id_str)
        
        except JWTError as e:
            raise ValueError(f"Invalid or expired reset token: {str(e)}")


    def reset_password(self, token: str, new_password: str) -> dict:
        """
        Reset le password d'un user avec un token valide
        
        Args:
            token: Token JWT de reset
            new_password: Nouveau password en clair
        
        Returns:
            dict: Message de succès
        
        Raises:
            ValueError: Si token invalide ou user non trouvé
        """
        # Vérifier le token
        user_id = self.verify_reset_token(token)
        
        # Récupérer le user
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Hash et update le password
        user.hashed_password = self.hash_password(new_password)
        self.db.commit()
        
        return {"message": "Password reset successful"}