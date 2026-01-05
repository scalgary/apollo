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

    def send_reset_email(self, to_email: str, reset_link: str):
        # MODE DEV - pas de config email
        if not all([self.email_from, self.email_password]):
            print("\n" + "="*80)
            print(f"📧 PASSWORD RESET EMAIL")
            print(f"To: {to_email}")
            print(f"🔗 Link: {reset_link}")
            print("="*80 + "\n")
            return
        
        # MODE PROD - envoi Gmail avec HTML
        subject = "Reset your Apollo password"
        html_body = f"""
        <html>
            <body>
                <p>Hello,</p>
                <p>You requested to reset your password for Apollo.</p>
                <p><a href="{reset_link}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Reset Password</a></p>
                <p>Or copy this link: <a href="{reset_link}">{reset_link}</a></p>
                <p>This link will expire in 1 hour.</p>
                <p>See you on the court! 🏓</p>
                <p>— The Apollo Team</p>
            </body>
        </html>
        """
        
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email_from
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(html_body, 'html'))  # ← HTML au lieu de 'plain'
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10)
            server.starttls()
            server.login(self.email_from, self.email_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"✅ Reset email sent to {to_email}")
            
        except Exception as e:
            logger.error(f"❌ Failed to send reset email: {e}")
            raise
        


    def send_message_notification(self, to_emails: list[str], author_name: str, message_content: str, is_comment: bool = False, original_author: str = None) -> bool:
        """
        Envoyer notification quand un message ou commentaire est posté
        
        En mode production: juste logger (pas d'envoi)
        En mode développement: envoie via Gmail SMTP
        
        Args:
            to_emails: Liste d'emails à notifier
            author_name: Nom de l'auteur du message/commentaire
            message_content: Contenu du message/commentaire
            is_comment: True si c'est un commentaire, False si message
            original_author: Si commentaire, nom de l'auteur du message original
        
        Returns:
            bool: True si emails envoyés (ou logged), False sinon
        """
        
        # MODE PRODUCTION: juste logger (pas d'envoi)
        if ENVIRONMENT == 'production':
            logger.info("=" * 80)
            if is_comment:
                logger.info(f"💬 NEW COMMENT NOTIFICATION (PRODUCTION - NOT SENT)")
                logger.info(f"📧 To: {', '.join(to_emails)}")
                logger.info(f"👤 Author: {author_name}")
                logger.info(f"📝 Comment on {original_author}'s message: {message_content[:50]}...")
            else:
                logger.info(f"📢 NEW MESSAGE NOTIFICATION (PRODUCTION - NOT SENT)")
                logger.info(f"📧 To: {', '.join(to_emails)}")
                logger.info(f"👤 Author: {author_name}")
                logger.info(f"📝 Message: {message_content[:50]}...")
            logger.info("=" * 80)
            return True
        
        # MODE DÉVELOPPEMENT: envoyer vrais emails via Gmail
        
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

Visit Apollo to see the full conversation: https://apollo-uenp.onrender.com/community

See you on the court! 🏓

— The Apollo Team
"""
        else:
            subject = f"Apollo - New message from {author_name}"
            body = f"""Hello,

{author_name} posted a new message:

"{message_content}"

Visit Apollo to see the message and reply: https://apollo-uenp.onrender.com/community

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