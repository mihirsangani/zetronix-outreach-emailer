"""Main campaign manager for outreach email automation."""

import time
from typing import List, Optional, Dict, Any, Callable
from .models import Lead, EmailTemplate, GeneratedEmail, CampaignStats, EmailStatus
from .sheets_client import GoogleSheetsClient
from .openai_client import OpenAIEmailGenerator
from .email_sender import SMTPEmailSender
from .logging_utils import get_logger

logger = get_logger(__name__)


class OutreachCampaign:
    """Main campaign manager for outreach email automation."""
    
    def __init__(
        self,
        sheets_client: Optional[GoogleSheetsClient] = None,
        email_generator: Optional[OpenAIEmailGenerator] = None,
        email_sender: Optional[SMTPEmailSender] = None
    ):
        """Initialize outreach campaign.
        
        Args:
            sheets_client: Google Sheets client
            email_generator: OpenAI email generator
            email_sender: SMTP email sender
        """
        self.sheets_client = sheets_client or GoogleSheetsClient()
        self.email_generator = email_generator or OpenAIEmailGenerator()
        self.email_sender = email_sender or SMTPEmailSender()
        
        self.stats = CampaignStats()
        self.generated_emails: List[GeneratedEmail] = []
        
        logger.info("Outreach campaign initialized")
    
    def run_campaign(
        self,
        template: EmailTemplate,
        leads_sheet: Optional[str] = None,
        results_sheet: Optional[str] = None,
        send_emails: bool = False,
        dry_run: bool = False,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        reply_to: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable] = None
    ) -> CampaignStats:
        """Run complete outreach campaign.
        
        Args:
            template: Email template to use
            leads_sheet: Name of leads sheet (optional)
            results_sheet: Name of results sheet (optional)
            send_emails: Whether to send emails via SMTP
            dry_run: If True, don't actually send emails
            from_email: Sender email address
            from_name: Sender display name
            reply_to: Reply-to email address
            context: Additional context for email generation
            progress_callback: Progress callback function
            
        Returns:
            Campaign statistics
        """
        try:
            logger.info("Starting outreach campaign")
            self.stats = CampaignStats()
            
            # Step 1: Read leads from Google Sheets
            if progress_callback:
                progress_callback("Reading leads from Google Sheets...")
            
            leads = self._read_leads(leads_sheet)
            self.stats.total_leads = len(leads)
            
            if not leads:
                logger.warning("No leads found - campaign aborted")
                return self.stats
            
            # Step 2: Generate emails
            if progress_callback:
                progress_callback(f"Generating personalized emails for {len(leads)} leads...")
            
            self.generated_emails = self._generate_emails(leads, template, context, progress_callback)
            self.stats.emails_generated = len(self.generated_emails)
            
            # Count successful generations
            successful_emails = [e for e in self.generated_emails if e.status == EmailStatus.GENERATED]
            failed_emails = [e for e in self.generated_emails if e.status == EmailStatus.FAILED]
            self.stats.emails_failed = len(failed_emails)
            
            logger.info(f"Email generation completed: {len(successful_emails)} successful, {len(failed_emails)} failed")
            
            # Step 3: Send emails (if requested)
            if send_emails and successful_emails:
                if progress_callback:
                    progress_callback(f"Sending {len(successful_emails)} emails...")
                
                send_stats = self._send_emails(
                    successful_emails, 
                    from_email, 
                    from_name, 
                    reply_to, 
                    dry_run, 
                    progress_callback
                )
                self.stats.emails_sent = send_stats.get('sent', 0)
                self.stats.emails_failed += send_stats.get('failed', 0)
                
                # Update A/B testing stats
                for email in successful_emails:
                    if email.status == EmailStatus.SENT:
                        if email.ab_variant and email.ab_variant.value == 'A':
                            self.stats.variant_a_sent += 1
                        elif email.ab_variant and email.ab_variant.value == 'B':
                            self.stats.variant_b_sent += 1
            
            # Step 4: Save results to Google Sheets
            if progress_callback:
                progress_callback("Saving results to Google Sheets...")
            
            self._save_results(results_sheet)
            
            # Finalize stats
            self.stats.end_time = time.time()
            
            logger.info(f"Campaign completed: {self.stats.emails_sent} sent, {self.stats.emails_failed} failed")
            return self.stats
            
        except Exception as e:
            logger.error(f"Campaign failed: {e}")
            raise
    
    def _read_leads(self, sheet_name: Optional[str] = None) -> List[Lead]:
        """Read leads from Google Sheets.
        
        Args:
            sheet_name: Name of the leads sheet
            
        Returns:
            List of leads
        """
        try:
            leads = self.sheets_client.read_leads(sheet_name)
            logger.info(f"Read {len(leads)} leads from Google Sheets")
            return leads
        except Exception as e:
            logger.error(f"Failed to read leads: {e}")
            raise
    
    def _generate_emails(
        self,
        leads: List[Lead],
        template: EmailTemplate,
        context: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable] = None
    ) -> List[GeneratedEmail]:
        """Generate emails for leads.
        
        Args:
            leads: List of leads
            template: Email template
            context: Additional context
            progress_callback: Progress callback function
            
        Returns:
            List of generated emails
        """
        def generation_progress(current: int, total: int, email: GeneratedEmail):
            """Progress callback for email generation."""
            if progress_callback:
                status = "✓" if email.status == EmailStatus.GENERATED else "✗"
                progress_callback(f"Generating emails: {current}/{total} {status} {email.lead.email}")
        
        try:
            emails = self.email_generator.generate_batch(
                leads, 
                template, 
                context, 
                generation_progress
            )
            
            logger.info(f"Generated {len(emails)} emails")
            return emails
            
        except Exception as e:
            logger.error(f"Failed to generate emails: {e}")
            raise
    
    def _send_emails(
        self,
        emails: List[GeneratedEmail],
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        reply_to: Optional[str] = None,
        dry_run: bool = False,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, int]:
        """Send emails via SMTP.
        
        Args:
            emails: List of generated emails
            from_email: Sender email address
            from_name: Sender display name
            reply_to: Reply-to email address
            dry_run: If True, don't actually send emails
            progress_callback: Progress callback function
            
        Returns:
            Sending statistics
        """
        def sending_progress(current: int, total: int, email: GeneratedEmail, success: bool):
            """Progress callback for email sending."""
            if progress_callback:
                status = "✓" if success else "✗"
                mode = " (DRY RUN)" if dry_run else ""
                progress_callback(f"Sending emails: {current}/{total} {status} {email.lead.email}{mode}")
        
        try:
            stats = self.email_sender.send_batch(
                emails,
                from_email,
                from_name,
                reply_to,
                dry_run,
                sending_progress
            )
            
            logger.info(f"Email sending completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to send emails: {e}")
            raise
    
    def _save_results(self, sheet_name: Optional[str] = None):
        """Save results to Google Sheets.
        
        Args:
            sheet_name: Name of the results sheet
        """
        try:
            if self.generated_emails:
                self.sheets_client.write_results(self.generated_emails, sheet_name)
                logger.info("Results saved to Google Sheets")
            else:
                logger.warning("No results to save")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
            # Don't raise - saving results is not critical
    
    def get_campaign_stats(self) -> CampaignStats:
        """Get campaign statistics.
        
        Returns:
            Campaign statistics
        """
        return self.stats
    
    def get_generated_emails(self) -> List[GeneratedEmail]:
        """Get list of generated emails.
        
        Returns:
            List of generated emails
        """
        return self.generated_emails
    
    def preview_emails(
        self,
        template: EmailTemplate,
        leads_sheet: Optional[str] = None,
        max_previews: int = 5,
        context: Optional[Dict[str, Any]] = None
    ) -> List[GeneratedEmail]:
        """Preview generated emails without sending.
        
        Args:
            template: Email template
            leads_sheet: Name of leads sheet
            max_previews: Maximum number of previews to generate
            context: Additional context
            
        Returns:
            List of preview emails
        """
        try:
            logger.info(f"Generating email previews (max {max_previews})")
            
            # Read limited number of leads
            leads = self.sheets_client.read_leads(leads_sheet)
            preview_leads = leads[:max_previews]
            
            # Generate emails
            preview_emails = []
            for lead in preview_leads:
                email = self.email_generator.generate_email(lead, template, context)
                preview_emails.append(email)
            
            logger.info(f"Generated {len(preview_emails)} preview emails")
            return preview_emails
            
        except Exception as e:
            logger.error(f"Failed to generate previews: {e}")
            raise
    
    def test_integrations(self) -> Dict[str, bool]:
        """Test all integrations.
        
        Returns:
            Dictionary with test results
        """
        results = {}
        
        # Test Google Sheets
        try:
            sheet_info = self.sheets_client.get_sheet_info()
            results['google_sheets'] = bool(sheet_info)
            logger.info(f"Google Sheets test: {'✓' if results['google_sheets'] else '✗'}")
        except Exception as e:
            results['google_sheets'] = False
            logger.error(f"Google Sheets test failed: {e}")
        
        # Test SMTP
        try:
            results['smtp'] = self.email_sender.test_connection()
            logger.info(f"SMTP test: {'✓' if results['smtp'] else '✗'}")
        except Exception as e:
            results['smtp'] = False
            logger.error(f"SMTP test failed: {e}")
        
        # Test OpenAI (simple test)
        try:
            # Create a simple test lead and template
            test_lead = Lead(
                email="test@example.com",
                first_name="John",
                last_name="Doe",
                company="Test Company"
            )
            test_template = EmailTemplate(
                name="test",
                subject_template="Hello {{first_name}}!",
                body_template="Hi {{first_name}}, this is a test email."
            )
            
            email = self.email_generator.generate_email(test_lead, test_template)
            results['openai'] = email.status == EmailStatus.GENERATED
            logger.info(f"OpenAI test: {'✓' if results['openai'] else '✗'}")
            
        except Exception as e:
            results['openai'] = False
            logger.error(f"OpenAI test failed: {e}")
        
        return results