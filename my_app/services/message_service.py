from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from db_models import Message, Comment, User, Admin
from services.admin_service import AdminService
from services.email_service import EmailService


class MessageService:
    """Service pour gérer les messages et commentaires"""
    
    def __init__(self, db: Session):
        self.db = db
        self.admin_service = AdminService(db)
        self.email_service = EmailService()
    
    
    # ============================================
    # MESSAGES CRUD
    # ============================================
    
    def create_message(self, user_id: int, content: str) -> dict:
        """
        Créer un nouveau message
        
        Args:
            user_id: ID de l'auteur
            content: Contenu du message (max 500 char)
        
        Returns:
            dict: Message créé avec infos auteur
        
        Raises:
            ValueError: Si contenu invalide
        """
        # Validation
        content = content.strip()
        if not content:
            raise ValueError("Message content cannot be empty")
        if len(content) > 500:
            raise ValueError("Message content cannot exceed 500 characters")
        
        # Récupérer l'auteur
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        # Créer le message
        new_message = Message(
            author_id=user_id,
            content=content
        )
        self.db.add(new_message)
        self.db.commit()
        self.db.refresh(new_message)
        
        # Envoyer notifications email
        is_admin = self.admin_service.is_user_admin(user_id)
        
        if is_admin:
            # Admin poste → notifier tous les users
            all_admin_emails = self.admin_service.get_admin_emails()
            all_users = self.db.query(User).all()
            #to_emails = [u.email for u in all_users if u.id != user_id]  # Pas l'auteur
            to_emails = [email for email in all_admin_emails if email != user.email]  # Pas l'auteur

        else:
            # User normal poste → notifier les admins
            to_emails = self.admin_service.get_admin_emails()
        
        if to_emails:
            self.email_service.send_message_notification(
                to_emails=to_emails,
                author_name=user.display_name,
                message_content=content,
                is_comment=False
            )
        
        result = {
            'id': new_message.id,
            'author_id': user_id,
            'author_name': user.display_name,
            'content': content,
            'created_at': new_message.created_at,
            'updated_at': new_message.updated_at
        }
        return self._serialize_datetime(result)  # ← AJOUTER CETTE LIGNE

    
    
    def edit_message(self, message_id: int, user_id: int, new_content: str) -> dict:
        """
        Éditer un message existant
        
        Args:
            message_id: ID du message
            user_id: ID de l'utilisateur (doit être l'auteur)
            new_content: Nouveau contenu
        
        Returns:
            dict: Message mis à jour
        
        Raises:
            ValueError: Si message pas trouvé ou user pas autorisé
        """
        # Validation contenu
        new_content = new_content.strip()
        if not new_content:
            raise ValueError("Message content cannot be empty")
        if len(new_content) > 500:
            raise ValueError("Message content cannot exceed 500 characters")
        
        # Récupérer le message
        message = self.db.query(Message).filter(Message.id == message_id).first()
        if not message:
            raise ValueError("Message not found")
        
        # Vérifier que user est l'auteur
        if message.author_id != user_id:
            raise ValueError("You can only edit your own messages")
        
        # Mettre à jour
        message.content = new_content
        message.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(message)
        
        # Récupérer le nom de l'auteur
        user = self.db.query(User).filter(User.id == user_id).first()
        
        result = {
            'id': message.id,
            'author_name': user.display_name,
            'content': message.content,
            'created_at': message.created_at,
            'updated_at': message.updated_at
        }

        return self._serialize_datetime(result)  # ← AJOUTER CETTE LIGNE

    
    
    def delete_message(self, message_id: int, user_id: int) -> dict:
        """
        Supprimer un message
        
        Autorisé si: user est l'auteur OU user est admin
        
        Args:
            message_id: ID du message
            user_id: ID de l'utilisateur
        
        Returns:
            dict: Message de succès
        
        Raises:
            ValueError: Si message pas trouvé ou pas autorisé
        """
        # Récupérer le message
        message = self.db.query(Message).filter(Message.id == message_id).first()
        if not message:
            raise ValueError("Message not found")
        
        # Vérifier permissions
        is_author = message.author_id == user_id
        is_admin = self.admin_service.is_user_admin(user_id)
        
        if not (is_author or is_admin):
            raise ValueError("You can only delete your own messages")
        
        # Supprimer (CASCADE supprime les commentaires auto)
        self.db.delete(message)
        self.db.commit()
        
        return {"success": True, "message": "Message deleted"}
    
    
    # ============================================
    # COMMENTAIRES CRUD
    # ============================================
    
    
    def create_comment(self, message_id: int, user_id: int, content: str) -> dict:
        """
            un commentaire sur un message
        
        Args:
            message_id: ID du message parent
            user_id: ID de l'auteur du commentaire
            content: Contenu du commentaire (max 500 char)
        
        Returns:
            dict: Commentaire créé
        
        Raises:
            ValueError: Si message pas trouvé ou contenu invalide
        """
        # Validation
        content = content.strip()
        if not content:
            raise ValueError("Comment content cannot be empty")
        if len(content) > 500:
            raise ValueError("Comment content cannot exceed 500 characters")
        
        # Vérifier que le message existe
        message = self.db.query(Message).filter(Message.id == message_id).first()
        if not message:
            raise ValueError("Message not found")
        
        # Récupérer l'auteur du commentaire
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        # Créer le commentaire
        new_comment = Comment(
            message_id=message_id,
            author_id=user_id,
            content=content
        )
        self.db.add(new_comment)
        self.db.commit()
        self.db.refresh(new_comment)
        
        # Envoyer notification à l'auteur du message original
        message_author = self.db.query(User).filter(User.id == message.author_id).first()
        
        if message_author and message_author.id != user_id:  # Pas notifier si on commente son propre message
            self.email_service.send_message_notification(
                to_emails=[message_author.email],
                author_name=user.display_name,
                message_content=content,
                is_comment=True,
                original_author=message_author.display_name
            )
        
        result = {
            'id': new_comment.id,
            'message_id': message_id,
            'author_id': user_id,
            'author_name': user.display_name,
            'content': content,
            'created_at': new_comment.created_at,
            'updated_at': new_comment.updated_at
        }
        return self._serialize_datetime(result)

    def edit_comment(self, comment_id: int, user_id: int, new_content: str) -> dict:
        """
        Éditer un commentaire existant
        
        Args:
            comment_id: ID du commentaire
            user_id: ID de l'utilisateur (doit être l'auteur)
            new_content: Nouveau contenu
        
        Returns:
            dict: Commentaire mis à jour
        
        Raises:
            ValueError: Si commentaire pas trouvé ou pas autorisé
        """
        # Validation
        new_content = new_content.strip()
        if not new_content:
            raise ValueError("Comment content cannot be empty")
        if len(new_content) > 500:
            raise ValueError("Comment content cannot exceed 500 characters")
        
        # Récupérer le commentaire
        comment = self.db.query(Comment).filter(Comment.id == comment_id).first()
        if not comment:
            raise ValueError("Comment not found")
        
        # Vérifier que user est l'auteur
        if comment.author_id != user_id:
            raise ValueError("You can only edit your own comments")
        
        # Mettre à jour
        comment.content = new_content
        comment.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(comment)
        
        # Récupérer le nom de l'auteur
        user = self.db.query(User).filter(User.id == user_id).first()
        
        result = {
            'id': comment.id,
            'author_name': user.display_name,
            'content': comment.content,
            'created_at': comment.created_at,
            'updated_at': comment.updated_at
        }
        return self._serialize_datetime(result)  # ← AJOUTER CETTE LIGNE

    
    
    def delete_comment(self, comment_id: int, user_id: int) -> dict:
        """
        Supprimer un commentaire
        
        Autorisé si: user est l'auteur OU user est admin
        
        Args:
            comment_id: ID du commentaire
            user_id: ID de l'utilisateur
        
        Returns:
            dict: Message de succès
        
        Raises:
            ValueError: Si commentaire pas trouvé ou pas autorisé
        """
        # Récupérer le commentaire
        comment = self.db.query(Comment).filter(Comment.id == comment_id).first()
        if not comment:
            raise ValueError("Comment not found")
        
        # Vérifier permissions
        is_author = comment.author_id == user_id
        is_admin = self.admin_service.is_user_admin(user_id)
        
        if not (is_author or is_admin):
            raise ValueError("You can only delete your own comments")
        
        # Supprimer
        self.db.delete(comment)
        self.db.commit()
        
        return {"success": True, "message": "Comment deleted"}
    
    
    
    # ============================================
    # RÉCUPÉRATION DONNÉES
    # ============================================
    
    def get_all_messages_with_comments(self) -> list[dict]:
        """
        Récupérer tous les messages avec leurs commentaires
        
        Ordre: messages les plus récents en premier
        
        Returns:
            list[dict]: Liste de messages avec commentaires imbriqués
        """
        # Query tous les messages (ordre DESC = plus récent d'abord)
        messages = self.db.query(Message).order_by(Message.created_at.desc()).all()
        
        result = []
        
        for message in messages:
            # Récupérer l'auteur du message
            author = self.db.query(User).filter(User.id == message.author_id).first()
            
            # Récupérer les commentaires (ordre ASC = plus ancien d'abord)
            comments_query = self.db.query(Comment).filter(
                Comment.message_id == message.id
            ).order_by(Comment.created_at.asc()).all()
            
            # Formater les commentaires
            comments = []
            for comment in comments_query:
                comment_author = self.db.query(User).filter(User.id == comment.author_id).first()
                comments.append({
                'id': comment.id,
                'author_id': comment.author_id,
                'author_name': comment_author.display_name if comment_author else 'Unknown',
                'content': comment.content,
                'created_at': comment.created_at.isoformat(),
                'created_at_display': comment.created_at.strftime('%b %d, %I:%M %p'),  # ← AJOUTER
                'updated_at': comment.updated_at.isoformat()
                })
            # Ajouter le message avec ses commentaires
            result.append({
            'id': message.id,
            'author_id': message.author_id,
            'author_name': author.display_name if author else 'Unknown',
            'content': message.content,
            'created_at': message.created_at.isoformat(),
            'created_at_display': message.created_at.strftime('%b %d, %Y at %I:%M %p'),  # ← AJOUTER
            'updated_at': message.updated_at.isoformat(),
            'comments': comments    
            })
        return result
    
    
    # ============================================
    # CLEANUP AUTOMATIQUE
    # ============================================
    
    def cleanup_old_messages(self) -> dict:
        """
        Supprimer les messages > 1 mois sans nouveaux commentaires
        
        Règles:
        - Si message SANS commentaires: vérifier date du message
        - Si message AVEC commentaires: vérifier date du dernier commentaire
        - NE PAS supprimer les messages postés par des admins
        
        Returns:
            dict: Nombre de messages supprimés
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
        deleted_count = 0
        
        # Query tous les messages
        messages = self.db.query(Message).all()
        
        for message in messages:
            # Vérifier si l'auteur est admin
            is_admin = self.admin_service.is_user_admin(message.author_id)
            
            if is_admin:
                # Skip les messages d'admins
                continue
            
            # Récupérer les commentaires du message
            comments = self.db.query(Comment).filter(
                Comment.message_id == message.id
            ).order_by(Comment.created_at.desc()).all()
            
            should_delete = False
            
            if comments:
                # Il y a des commentaires: vérifier le plus récent
                last_comment = comments[0]
                if last_comment.created_at < cutoff_date:
                    should_delete = True
            else:
                # Pas de commentaires: vérifier la date du message
                if message.created_at < cutoff_date:
                    should_delete = True
            
            if should_delete:
                self.db.delete(message)
                deleted_count += 1
        
        self.db.commit()
        
        return {
            'deleted_count': deleted_count,
            'cutoff_date': cutoff_date.isoformat()
        }
    
    def _serialize_datetime(self, obj: dict) -> dict:
        """Convertit les datetime en ISO format pour JSON"""
        if 'created_at' in obj and obj['created_at']:
            obj['created_at'] = obj['created_at'].isoformat()
        if 'updated_at' in obj and obj['updated_at']:
            obj['updated_at'] = obj['updated_at'].isoformat()
        return obj
    
    def _format_datetime_display(self, dt_iso: str) -> str:
        """Convertit ISO datetime en format lisible"""
        from datetime import datetime
        dt = datetime.fromisoformat(dt_iso.replace('Z', '+00:00'))
        return dt.strftime('%b %d, %Y at %I:%M %p')