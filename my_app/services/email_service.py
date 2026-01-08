import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import resend
logger = logging.getLogger(__name__)

ENVIRONMENT = os.getenv('ENVIRONMENT', 'production')

class EmailService:
    """Service pour gérer l'envoi d'emails"""
        
    def __init__(self):
        self.email_from = os.environ.get('EMAIL_FROM')
        self.email_password = os.environ.get('EMAIL_PASSWORD')
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', '587'))  

    def send_reset_email(self, to_email: str, reset_link: str):
        if not self.email_from or not self.email_password:
            print(f"📧 Reset link: {reset_link}")
            return
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_from
            msg['To'] = to_email
            msg['Subject'] = "Reset your Apollo password"
            
            body = f"""
    Hello,

    Click to reset your password:
    {reset_link}

    Expires in 1 hour.

    🏓 The Apollo Team
    """
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10)
            server.starttls()
            server.login(self.email_from, self.email_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"✅ Email sent to {to_email}")
        except Exception as e:
            logger.error(f"❌ Email failed: {e}")


    def send_message_notification(self, to_emails: list[str], author_name: str, message_content: str, is_comment: bool = False, original_author: str = None) -> bool:
        """
        Envoyer notification à tous les users signés
        
        Args:
            to_emails: Liste d'emails à notifier
            author_name: Nom de l'auteur
            message_content: Contenu
            is_comment: True si commentaire, False si message
            original_author: Si commentaire, nom de l'auteur original
        
        Returns:
            bool: True si au moins 1 email envoyé
        """
        
        print(f"📧 send_message_notification called")
        print(f"📧 to_emails: {to_emails}")
        print(f"📧 EMAIL_FROM: {self.email_from}")
        print(f"📧 EMAIL_PASSWORD exists: {bool(self.email_password)}")
        
        # Vérifier configuration
        if not self.email_from or not self.email_password:
            logger.error("❌ Email configuration missing")
            print("❌ Missing EMAIL config - NOT SENDING")
            return False
        
        # Préparer sujet et body
        if is_comment:
            subject = f"Apollo - New comment from {author_name}"
            body = f"""Hello,

    {author_name} commented on {original_author}'s message:

    "{message_content}"

    Visit Apollo: http://132.226.96.197:8000/community

    🏓 The Apollo Team
    """
        else:
            subject = f"Apollo - New message from {author_name}"
            body = f"""Hello,

    {author_name} posted a new message:

    "{message_content}"

    Visit Apollo: http://132.226.96.197:8000/community

    🏓 The Apollo Team
    """
        
        # Envoyer à tous
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
                
                logger.info(f"✅ Email sent to {to_email}")
                print(f"✅ Email sent to {to_email}")
                success_count += 1
                
            except Exception as e:
                logger.error(f"❌ Failed: {to_email}: {e}")
                print(f"❌ Failed: {to_email}: {e}")
        
        print(f"📧 Total sent: {success_count}/{len(to_emails)}")
        return success_count > 0