"""
Email notification service for Birds with Friends.

Supports both SMTP and SendGrid for reliable email delivery with templates
and comprehensive error handling.
"""
import logging
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText as MimeText
from email.mime.multipart import MIMEMultipart as MimeMultipart
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import asyncio
import os

import sendgrid
from sendgrid.helpers.mail import Mail

logger = logging.getLogger(__name__)


class EmailProvider(ABC):
    """Abstract base class for email providers."""
    
    @abstractmethod
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str
    ) -> Dict[str, Any]:
        """Send email and return delivery status."""
        pass


class SMTPProvider(EmailProvider):
    """SMTP email provider for development and basic use."""
    
    def __init__(
        self,
        smtp_server: str = "localhost",
        smtp_port: int = 587,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: bool = True,
        from_email: str = "noreply@birdswithfriends.com"
    ):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.from_email = from_email
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str
    ) -> Dict[str, Any]:
        """Send email via SMTP."""
        
        try:
            # Create message
            msg = MimeMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email
            
            # Add text and HTML parts
            text_part = MimeText(text_content, 'plain')
            html_part = MimeText(html_content, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send via SMTP
            if self.smtp_server == "localhost" or self.smtp_server == "127.0.0.1":
                # Development mode - just log the email
                logger.info(f"📧 [DEV MODE] Email to {to_email}: {subject}")
                logger.info(f"Content: {text_content[:200]}...")
                
                return {
                    "success": True,
                    "provider": "smtp_dev",
                    "message_id": f"dev_{datetime.now().timestamp()}"
                }
            
            # Production SMTP
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            
            if self.use_tls:
                server.starttls()
            
            if self.username and self.password:
                server.login(self.username, self.password)
            
            server.send_message(msg)
            server.quit()
            
            logger.info(f"📧 Email sent successfully to {to_email}")
            
            return {
                "success": True,
                "provider": "smtp",
                "message_id": f"smtp_{datetime.now().timestamp()}"
            }
            
        except Exception as e:
            logger.error(f"SMTP email failed to {to_email}: {e}")
            return {
                "success": False,
                "provider": "smtp",
                "error": str(e)
            }


class SendGridProvider(EmailProvider):
    """SendGrid email provider for production use."""
    
    def __init__(
        self,
        api_key: str,
        from_email: str = "noreply@birdswithfriends.com",
        from_name: str = "Birds with Friends"
    ):
        self.api_key = api_key
        self.from_email = from_email
        self.from_name = from_name
        self.client = sendgrid.SendGridAPIClient(api_key=api_key)
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str
    ) -> Dict[str, Any]:
        """Send email via SendGrid."""
        
        try:
            message = Mail(
                from_email=(self.from_email, self.from_name),
                to_emails=to_email,
                subject=subject,
                html_content=html_content,
                plain_text_content=text_content
            )
            
            response = self.client.send(message)
            
            logger.info(f"📧 SendGrid email sent to {to_email} (status: {response.status_code})")
            
            return {
                "success": response.status_code in [200, 202],
                "provider": "sendgrid",
                "message_id": response.headers.get("X-Message-Id"),
                "status_code": response.status_code
            }
            
        except Exception as e:
            logger.error(f"SendGrid email failed to {to_email}: {e}")
            return {
                "success": False,
                "provider": "sendgrid", 
                "error": str(e)
            }


class EmailTemplates:
    """Email templates for different notification types."""
    
    @staticmethod
    def episode_published(
        episode_title: str,
        episode_index: int,
        story_title: str,
        episode_summary: str,
        episode_link: str
    ) -> Dict[str, str]:
        """Generate episode published email content."""
        
        subject = f"Your Birds with Friends episode #{episode_index} is ready! 🐦"
        
        # Text version
        text_content = f"""
Hi there!

Your new Birds with Friends episode is ready to read:

{episode_title}
Episode #{episode_index} of "{story_title}"

{episode_summary}

Read the full episode here: {episode_link}

Happy reading!
The Birds with Friends Team

---
You're receiving this because you subscribed to episode notifications.
To unsubscribe, visit: {episode_link}/unsubscribe
        """.strip()
        
        # HTML version
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #4facfe, #00f2fe); color: white; padding: 20px; border-radius: 10px; text-align: center; }}
        .content {{ padding: 20px; background: #f9f9f9; border-radius: 10px; margin: 20px 0; }}
        .episode-info {{ background: white; padding: 15px; border-radius: 5px; margin: 15px 0; }}
        .cta-button {{ display: inline-block; background: #4facfe; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; }}
        .footer {{ text-align: center; font-size: 12px; color: #666; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🐦 New Episode Ready!</h1>
        <p>Your Birds with Friends story continues...</p>
    </div>
    
    <div class="content">
        <div class="episode-info">
            <h2>{episode_title}</h2>
            <p><strong>Episode #{episode_index}</strong> of "{story_title}"</p>
            <p>{episode_summary}</p>
        </div>
        
        <p style="text-align: center;">
            <a href="{episode_link}" class="cta-button">Read Episode Now</a>
        </p>
    </div>
    
    <div class="footer">
        <p>Happy reading!<br>The Birds with Friends Team</p>
        <p><a href="{episode_link}/unsubscribe">Unsubscribe from notifications</a></p>
    </div>
</body>
</html>
        """.strip()
        
        return {
            "subject": subject,
            "text": text_content,
            "html": html_content
        }


class EmailSender:
    """Main email notification service."""
    
    def __init__(
        self,
        provider: Optional[EmailProvider] = None,
        base_url: str = "http://localhost:3000"
    ):
        """Initialize email sender with provider."""
        
        if provider is None:
            # Auto-configure provider based on environment
            sendgrid_key = os.getenv("SENDGRID_API_KEY")
            
            if sendgrid_key:
                provider = SendGridProvider(
                    api_key=sendgrid_key,
                    from_email=os.getenv("FROM_EMAIL", "noreply@birdswithfriends.com")
                )
                logger.info("Using SendGrid email provider")
            else:
                # Development SMTP
                provider = SMTPProvider(
                    smtp_server=os.getenv("SMTP_SERVER", "localhost"),
                    smtp_port=int(os.getenv("SMTP_PORT", "587")),
                    username=os.getenv("SMTP_USERNAME"),
                    password=os.getenv("SMTP_PASSWORD"),
                    from_email=os.getenv("FROM_EMAIL", "noreply@birdswithfriends.com")
                )
                logger.info("Using SMTP email provider (development mode)")
        
        self.provider = provider
        self.base_url = base_url
        self.templates = EmailTemplates()
    
    async def send_episode_notification(
        self,
        user_email: str,
        story_title: str,
        episode_title: str,
        episode_index: int,
        story_id: str,
        episode_summary: str = ""
    ) -> Dict[str, Any]:
        """Send episode published notification email."""
        
        # Generate episode link
        episode_link = f"{self.base_url}/stories/{story_id}/episodes/{episode_index}"
        
        # Generate email content from template
        email_content = self.templates.episode_published(
            episode_title=episode_title,
            episode_index=episode_index,
            story_title=story_title,
            episode_summary=episode_summary or f"Episode {episode_index} of your bird story is now available.",
            episode_link=episode_link
        )
        
        # Send email
        result = await self.provider.send_email(
            to_email=user_email,
            subject=email_content["subject"],
            html_content=email_content["html"],
            text_content=email_content["text"]
        )
        
        # Add metadata
        result.update({
            "notification_type": "email",
            "story_id": story_id,
            "episode_index": episode_index,
            "recipient": user_email
        })
        
        return result
    
    async def send_test_email(self, to_email: str) -> Dict[str, Any]:
        """Send test email to verify configuration."""
        
        subject = "Birds with Friends - Email Test"
        text_content = "This is a test email from Birds with Friends notification system."
        html_content = f"""
        <html>
        <body>
            <h2>🐦 Birds with Friends Email Test</h2>
            <p>This is a test email from the Birds with Friends notification system.</p>
            <p>If you received this, email notifications are working correctly!</p>
            <p>Timestamp: {datetime.now(timezone.utc).isoformat()}</p>
        </body>
        </html>
        """
        
        result = await self.provider.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
        
        result.update({
            "notification_type": "test_email",
            "recipient": to_email
        })
        
        return result


# Global email sender instance
email_sender = EmailSender()