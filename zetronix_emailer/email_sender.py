"""SMTP email sender for outreach emails."""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict, Any
from .models import GeneratedEmail, EmailStatus
from .logging_utils import get_logger
from .config import config

logger = get_logger(__name__)


class SMTPEmailSender:
    """SMTP email sender with HTML support."""
    
    def __init__(
        self,
        smtp_server: Optional[str] = None,
        smtp_port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: Optional[bool] = None
    ):
        """Initialize SMTP email sender.
        
        Args:
            smtp_server: SMTP server hostname
            smtp_port: SMTP server port
            username: SMTP username
            password: SMTP password
            use_tls: Whether to use TLS encryption
        """
        self.smtp_server = smtp_server or config.smtp_server
        self.smtp_port = smtp_port or config.smtp_port
        self.username = username or config.smtp_username
        self.password = password or config.smtp_password
        self.use_tls = use_tls if use_tls is not None else config.smtp_use_tls
        
        # Validate configuration
        if not all([self.smtp_server, self.username, self.password]):
            logger.warning("SMTP configuration incomplete - email sending will be disabled")
            self.enabled = False
        else:
            self.enabled = True
            logger.info(f"SMTP sender configured: {self.smtp_server}:{self.smtp_port}")
    
    def send_email(
        self,
        email: GeneratedEmail,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        reply_to: Optional[str] = None,
        dry_run: bool = False
    ) -> bool:
        """Send a single email.
        
        Args:
            email: Generated email to send
            from_email: Sender email address (defaults to SMTP username)
            from_name: Sender display name
            reply_to: Reply-to email address
            dry_run: If True, don't actually send email
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        if not self.enabled:
            logger.error("SMTP sender not configured - cannot send email")
            email.mark_failed("SMTP not configured")
            return False
        
        if dry_run:
            logger.info(f"DRY RUN: Would send email to {email.lead.email}")
            email.mark_sent()
            return True
        
        try:
            logger.info(f"Sending email to {email.lead.email}")
            
            # Create message
            msg = self._create_message(email, from_email, from_name, reply_to)
            
            # Send email
            with self._get_smtp_connection() as server:
                server.send_message(msg)
            
            # Mark as sent
            email.mark_sent()
            logger.info(f"Successfully sent email to {email.lead.email}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to send email to {email.lead.email}: {e}"
            logger.error(error_msg)
            email.mark_failed(str(e))
            return False
    
    def send_batch(
        self,
        emails: List[GeneratedEmail],
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        reply_to: Optional[str] = None,
        dry_run: bool = False,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, int]:
        """Send a batch of emails.
        
        Args:
            emails: List of generated emails to send
            from_email: Sender email address
            from_name: Sender display name
            reply_to: Reply-to email address
            dry_run: If True, don't actually send emails
            progress_callback: Optional progress callback function
            
        Returns:
            Dictionary with sending statistics
        """
        if not self.enabled and not dry_run:
            logger.error("SMTP sender not configured - cannot send emails")
            return {'sent': 0, 'failed': len(emails)}
        
        logger.info(f"Starting batch email sending: {len(emails)} emails")
        
        stats = {'sent': 0, 'failed': 0}
        
        # Filter only generated emails (skip failed generations)
        sendable_emails = [e for e in emails if e.status == EmailStatus.GENERATED]
        
        for i, email in enumerate(sendable_emails):
            try:
                success = self.send_email(email, from_email, from_name, reply_to, dry_run)
                
                if success:
                    stats['sent'] += 1
                else:
                    stats['failed'] += 1
                
                if progress_callback:
                    progress_callback(i + 1, len(sendable_emails), email, success)
                
                # Small delay to avoid overwhelming SMTP server
                import time
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Unexpected error sending email {i+1}: {e}")
                stats['failed'] += 1
        
        logger.info(f"Batch sending completed: {stats['sent']} sent, {stats['failed']} failed")
        return stats
    
    def _create_message(
        self,
        email: GeneratedEmail,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> MIMEMultipart:
        """Create email message.
        
        Args:
            email: Generated email
            from_email: Sender email address
            from_name: Sender display name
            reply_to: Reply-to email address
            
        Returns:
            Email message object
        """
        # Create message
        msg = MIMEMultipart('alternative')
        
        # Set headers
        sender_email = from_email or self.username
        if from_name:
            msg['From'] = f"{from_name} <{sender_email}>"
        else:
            msg['From'] = sender_email
            
        msg['To'] = email.lead.email
        msg['Subject'] = email.subject
        
        if reply_to:
            msg['Reply-To'] = reply_to
        
        # A/B testing tracking header
        if email.ab_variant:
            msg['X-AB-Variant'] = email.ab_variant.value
        
        # Add text part
        text_part = MIMEText(email.body, 'plain', 'utf-8')
        msg.attach(text_part)
        
        # Add HTML part if available
        if email.html_body:
            html_part = MIMEText(email.html_body, 'html', 'utf-8')
            msg.attach(html_part)
        
        return msg
    
    def _get_smtp_connection(self):
        """Get SMTP connection.
        
        Returns:
            SMTP connection object
        """
        if self.use_tls:
            # Create secure connection
            context = ssl.create_default_context()
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls(context=context)
        else:
            # Create regular connection
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
        
        # Login
        server.login(self.username, self.password)
        
        return server
    
    def test_connection(self) -> bool:
        """Test SMTP connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        if not self.enabled:
            logger.error("SMTP not configured")
            return False
        
        try:
            logger.info("Testing SMTP connection...")
            
            with self._get_smtp_connection() as server:
                logger.info("SMTP connection test successful")
                return True
                
        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            return False
    
    def send_test_email(
        self,
        to_email: str,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None
    ) -> bool:
        """Send a test email.
        
        Args:
            to_email: Recipient email address
            from_email: Sender email address
            from_name: Sender display name
            
        Returns:
            True if test email sent successfully, False otherwise
        """
        if not self.enabled:
            logger.error("SMTP not configured")
            return False
        
        try:
            logger.info(f"Sending test email to {to_email}")
            
            # Create test message
            msg = MIMEMultipart('alternative')
            
            sender_email = from_email or self.username
            if from_name:
                msg['From'] = f"{from_name} <{sender_email}>"
            else:
                msg['From'] = sender_email
                
            msg['To'] = to_email
            msg['Subject'] = "Zetronix Emailer Test"
            
            # Test content
            text_content = """
This is a test email from Zetronix Outreach Emailer.

If you received this email, your SMTP configuration is working correctly.

Best regards,
Zetronix Emailer
            """.strip()
            
            html_content = """
            <html>
                <body>
                    <h2>Zetronix Emailer Test</h2>
                    <p>This is a test email from <strong>Zetronix Outreach Emailer</strong>.</p>
                    <p>If you received this email, your SMTP configuration is working correctly.</p>
                    <br>
                    <p>Best regards,<br>Zetronix Emailer</p>
                </body>
            </html>
            """
            
            # Add parts
            text_part = MIMEText(text_content, 'plain', 'utf-8')
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send
            with self._get_smtp_connection() as server:
                server.send_message(msg)
            
            logger.info(f"Test email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send test email: {e}")
            return False