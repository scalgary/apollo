import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logger = logging.getLogger(__name__)

ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

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