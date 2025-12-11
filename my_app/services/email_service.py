import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logger = logging.getLogger(__name__)

ENVIRONMENT = os.getenv('ENVIRONMENT', 'production')

class EmailService:
    """Service pour gérer l'envoi d'emails"""
    
    def __init__(self):
        self.email_from = os.environ.get('EMAIL_FROM')
        self.email_password = os.environ.get('EMAIL_PASSWORD')
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    
    def send_reset_email(self, to_email: str, reset_link: str) -> bool:
        """
        Envoyer email de reset password via SMTP
        
        En mode développement: affiche juste le lien dans les logs
        En mode production: envoie un vrai email SMTP
        
        Returns:
            bool: True si email envoyé (ou logged en dev), False sinon
        """
        
        # MODE DÉVELOPPEMENT: juste logger le lien
        if ENVIRONMENT == 'development':
            logger.info("=" * 80)
            logger.info("🔗 PASSWORD RESET LINK (DEV MODE)")
            logger.info(f"📧 To: {to_email}")
            logger.info(f"🔗 Link: {reset_link}")
            logger.info("=" * 80)
            return True
        
        # MODE PRODUCTION: envoyer vrai email
        
        # Vérifier configuration
        if not all([self.email_from, self.email_password]):
            logger.error("❌ Email configuration missing (EMAIL_FROM or EMAIL_PASSWORD)")
            return False
        
        # Email subject
        subject = "Apollo - Reset Your Password"
        
        # Email body
        body = f"""Hello,

You requested to reset your password for Apollo.

Click the link below to reset your password:
{reset_link}

This link will expire in 1 hour.

If you didn't request this, please ignore this email.

See you on the court! 🏓

— The Apollo Team
"""
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = self.email_from
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        try:
            logger.info(f"📧 Connecting to {self.smtp_server}:{self.smtp_port}...")
            server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10)
            server.starttls()
            logger.info(f"🔐 Logging in as {self.email_from}...")
            server.login(self.email_from, self.email_password)
            logger.info(f"📤 Sending reset email to {to_email}...")
            server.send_message(msg)
            server.quit()
            logger.info(f"✅ Reset email sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send reset email to {to_email}: {e}")
            return False
        
    def send_message_notification(self, to_emails: list[str], author_name: str, message_content: str, is_comment: bool = False, original_author: str = None) -> bool:
        """
        Envoyer notification quand un message ou commentaire est posté
        
        Args:
            to_emails: Liste d'emails à notifier
            author_name: Nom de l'auteur du message/commentaire
            message_content: Contenu du message/commentaire
            is_comment: True si c'est un commentaire, False si message
            original_author: Si commentaire, nom de l'auteur du message original
        
        Returns:
            bool: True si emails envoyés (ou logged en dev), False sinon
        """
        
        # MODE DÉVELOPPEMENT: juste logger
        if ENVIRONMENT == 'development':
            logger.info("=" * 80)
            if is_comment:
                logger.info(f"💬 NEW COMMENT NOTIFICATION (DEV MODE)")
                logger.info(f"📧 To: {', '.join(to_emails)}")
                logger.info(f"👤 Author: {author_name}")
                logger.info(f"📝 Comment on {original_author}'s message: {message_content[:50]}...")
            else:
                logger.info(f"📢 NEW MESSAGE NOTIFICATION (DEV MODE)")
                logger.info(f"📧 To: {', '.join(to_emails)}")
                logger.info(f"👤 Author: {author_name}")
                logger.info(f"📝 Message: {message_content[:50]}...")
            logger.info("=" * 80)
            return True
        
        # MODE PRODUCTION: envoyer vrais emails
        
        # Vérifier configuration
        if not all([self.email_from, self.email_password]):
            logger.error("❌ Email configuration missing")
            return False
        
        # Préparer sujet et body
        if is_comment:
            subject = f"Apollo - New comment from {author_name}"
            body = f"""Hello,

    {author_name} commented on {original_author}'s message:

    "{message_content}"

    Visit Apollo to see the full conversation: https://apollo-uenp.onrender.com/messages

    See you on the court! 🏓

    — The Apollo Team
    """
        else:
            subject = f"Apollo - New message from {author_name}"
            body = f"""Hello,

    {author_name} posted a new message:

    "{message_content}"

    Visit Apollo to see the message and reply: https://apollo-uenp.onrender.com/messages

    See you on the court! 🏓

    — The Apollo Team
    """
        
        # Envoyer à tous les destinataires
        success_count = 0
        for to_email in to_emails:
            try:
                msg = MIMEMultipart()
                msg['From'] = self.email_from
                msg['To'] = to_email
                msg['Subject'] = subject
                msg.attach(MIMEText(body, 'plain'))
                
                server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10)
                server.starttls()
                server.login(self.email_from, self.email_password)
                server.send_message(msg)
                server.quit()
                
                logger.info(f"✅ Notification sent to {to_email}")
                success_count += 1
                
            except Exception as e:
                logger.error(f"❌ Failed to send notification to {to_email}: {e}")
        
        return success_count > 0