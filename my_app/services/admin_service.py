from sqlalchemy.orm import Session
from db_models import Admin, User
from utils import load_events, load_event_types, load_admins



class AdminService:
    """Service pour gérer les administrateurs"""
    
    def __init__(self, db: Session):
        self.db = db
    
    
    def import_admins_from_csv(self):
        """
        Import admins depuis CSV dans la table admins.
        
        Logique:
        - Lit admins.csv (juste admin_email)
        - Crée entrée dans table admins avec user_id=NULL
        - Si admin_email existe déjà → update (rien à faire ici car juste email)
        - Si l'email correspond à un user existant → link automatiquement
        
        Returns:
            int: Nombre d'admins importés
        """
        admin_emails = load_admins()  # Liste d'emails
        imported_count = 0
        
        for admin_email in admin_emails:
            try:
                # 1. Vérifier si admin existe déjà
                existing_admin = self.db.query(Admin).filter(
                    Admin.admin_email == admin_email
                ).first()
                
                if existing_admin:
                    # Admin existe déjà, skip
                    continue
                
                # 2. Chercher si un user avec cet email existe
                user = self.db.query(User).filter(
                    User.email == admin_email
                ).first()
                
                # 3. Créer l'admin
                new_admin = Admin(
                    admin_email=admin_email,
                    user_id=user.id if user else None  # Link si user existe
                )
                self.db.add(new_admin)
                imported_count += 1
                
            except Exception as e:
                print(f"Error importing admin {admin_email}: {e}")
                continue
        
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