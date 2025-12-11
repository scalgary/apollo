from sqlalchemy.orm import Session
from db_models import Admin, User
from utils import load_events, load_event_types, load_admins



class AdminService:
    """Service pour gérer les administrateurs"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def import_admins_from_csv(self):
        """
        Import admins depuis CSV et créer leurs comptes users automatiquement.
        
        Logique:
        1. Lire admins.csv (admin_email, display_name, real_name)
        2. Lire env vars (ADMIN_EMAIL_1/2, ADMIN_PASSWORD_1/2)
        3. Pour chaque admin:
        - Créer user si n'existe pas
        - Créer memberships punch_card 0 crédits
        - Créer entrée dans table admins
        
        Returns:
            int: Nombre d'admins importés
        """
        pass

 
        from db_models import User, UserEventTypeMembership, EventType
        from services.auth_service import AuthService
        import os
    
        # 1. Charger admins.csv
        admins_data = load_admins()
    
            # 2. Charger passwords depuis env vars
        admin_passwords = {}
        for i in range(1, 3):  # ADMIN_EMAIL_1 et ADMIN_EMAIL_2
            email_key = f'ADMIN_EMAIL_{i}'
            password_key = f'ADMIN_PASSWORD_{i}'
            
            email = os.getenv(email_key)
            password = os.getenv(password_key)
            
            if email and password:
                admin_passwords[email.strip().lower()] = password
            elif email or password:
                # Un des deux manque
                raise ValueError(f"Missing {email_key} or {password_key} in environment variables")
        
        if not admin_passwords:
            raise ValueError("No admin passwords found in environment variables (ADMIN_EMAIL_1/2, ADMIN_PASSWORD_1/2)")
        
        # 3. Récupérer tous les event types
        event_types = self.db.query(EventType).all()
        if not event_types:
            print("Warning: No event types found, admins will have no memberships")
        
        auth_service = AuthService(self.db)
        imported_count = 0
        
        # 4. Pour chaque admin dans CSV
        for admin_data in admins_data:
            admin_email = admin_data['admin_email']
            display_name = admin_data['display_name']
            real_name = admin_data['real_name']
            
            # Vérifier que le password existe
            if admin_email not in admin_passwords:
                raise ValueError(f"Admin {admin_email} in CSV but no password in env vars")
            
            password = admin_passwords[admin_email]
            
            try:
                # 5. Vérifier si user existe déjà
                existing_user = self.db.query(User).filter(User.email == admin_email).first()
                
                if existing_user:
                    print(f"Admin user {admin_email} already exists, skipping user creation")
                    user_id = existing_user.id
                else:
                    # 6. Créer le user
                    hashed_password = auth_service.hash_password(password)
                    new_user = User(
                        email=admin_email,
                        hashed_password=hashed_password,
                        display_name=display_name,
                        real_name=real_name
                    )
                    self.db.add(new_user)
                    self.db.flush()  # Pour obtenir l'ID
                    user_id = new_user.id
                    print(f"✓ Created admin user: {admin_email}")
                    
                    # 7. Créer memberships punch_card 0 crédits pour tous les event types
                    for event_type in event_types:
                        membership = UserEventTypeMembership(
                            user_id=user_id,
                            event_type_id=event_type.id,
                            membership_type='punch_card',
                            total_credits_purchased=0,
                            remaining_credits=0
                        )
                        self.db.add(membership)
                    
                    print(f"✓ Created {len(event_types)} punch_card memberships (0 credits)")
                
                # 8. Créer/update entrée dans table admins
                existing_admin = self.db.query(Admin).filter(Admin.admin_email == admin_email).first()
                
                if not existing_admin:
                    new_admin = Admin(
                        user_id=user_id,
                        admin_email=admin_email
                    )
                    self.db.add(new_admin)
                    imported_count += 1
                    print(f"✓ Created admin entry for {admin_email}")
                else:
                    # Update user_id au cas où
                    existing_admin.user_id = user_id
                    print(f"✓ Updated admin entry for {admin_email}")
                
            except Exception as e:
                print(f"Error importing admin {admin_email}: {e}")
                raise
        
        self.db.commit()
        return imported_count
        

    def is_user_admin(self, user_id: int) -> bool:
        """
        Vérifie si un user_id est admin.
        
        Args:
            user_id: ID du user
        
        Returns:
            bool: True si admin, False sinon
        """
        admin = self.db.query(Admin).filter(Admin.user_id == user_id).first()
        return admin is not None
    
    
    def is_email_admin(self, email: str) -> bool:
        """
        Vérifie si un email est dans la liste des admins.
        
        Utile pour login/permissions basées sur email.
        
        Args:
            email: Email à vérifier
        
        Returns:
            bool: True si admin, False sinon
        """
        email_lower = email.strip().lower()
        admin = self.db.query(Admin).filter(Admin.admin_email == email_lower).first()
        return admin is not None
    
    
    def get_admin_emails(self) -> list[str]:
        """
        Récupère tous les emails admins pour notifications.
        
        Returns:
            list[str]: Liste des admin_email
        """
        admins = self.db.query(Admin).all()
        return [admin.admin_email for admin in admins]
    
    
    def link_user_to_admin(self, user_id: int, admin_email: str) -> bool:
        """
        Lie un user existant à un admin existant.
        
        Utile quand un admin s'inscrit comme user après coup.
        
        Args:
            user_id: ID du user
            admin_email: Email de l'admin
        
        Returns:
            bool: True si lien créé, False si admin pas trouvé
        """
        admin = self.db.query(Admin).filter(Admin.admin_email == admin_email).first()
        
        if not admin:
            return False
        
        # Update le user_id
        admin.user_id = user_id
        self.db.commit()
        return True