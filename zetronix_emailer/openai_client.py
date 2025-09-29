"""OpenAI integration for AI-powered email generation."""

import openai
import time
import random
from typing import List, Optional, Dict, Any
from jinja2 import Template
from .models import Lead, EmailTemplate, GeneratedEmail, ABTestVariant
from .logging_utils import get_logger
from .config import config

logger = get_logger(__name__)


class OpenAIEmailGenerator:
    """OpenAI-powered email generator with A/B testing support."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize OpenAI email generator.
        
        Args:
            api_key: OpenAI API key
            model: OpenAI model to use
        """
        self.api_key = api_key or config.openai_api_key
        self.model = model or config.openai_model
        
        # Configure OpenAI client
        self.client = openai.OpenAI(api_key=self.api_key)
        
        logger.info(f"Initialized OpenAI email generator with model: {self.model}")
    
    def generate_email(
        self,
        lead: Lead,
        template: EmailTemplate,
        context: Optional[Dict[str, Any]] = None
    ) -> GeneratedEmail:
        """Generate a personalized email for a lead.
        
        Args:
            lead: Lead information
            template: Email template
            context: Additional context for email generation
            
        Returns:
            Generated email object
        """
        start_time = time.time()
        
        try:
            logger.info(f"Generating email for {lead.email} using template: {template.name}")
            
            # Determine A/B variant
            ab_variant = None
            if template.ab_test_enabled and config.ab_test_enabled:
                ab_variant = self._determine_ab_variant()
            
            # Generate subject and body
            subject = self._generate_subject(lead, template, ab_variant, context)
            body = self._generate_body(lead, template, ab_variant, context)
            html_body = self._generate_html_body(lead, template, ab_variant, context)
            
            # Calculate generation time
            generation_time = int((time.time() - start_time) * 1000)
            
            # Create generated email object
            email = GeneratedEmail(
                lead=lead,
                template_name=template.name,
                subject=subject,
                body=body,
                html_body=html_body,
                ab_variant=ab_variant,
                openai_model_used=self.model,
                generation_time_ms=generation_time
            )
            
            logger.info(f"Successfully generated email for {lead.email} in {generation_time}ms")
            return email
            
        except Exception as e:
            logger.error(f"Failed to generate email for {lead.email}: {e}")
            
            # Create failed email object
            email = GeneratedEmail(
                lead=lead,
                template_name=template.name,
                subject="",
                body="",
                html_body="",
            )
            email.mark_failed(str(e))
            return email
    
    def _determine_ab_variant(self) -> ABTestVariant:
        """Determine A/B test variant based on configured split ratio.
        
        Returns:
            A/B test variant
        """
        return ABTestVariant.A if random.random() < config.ab_test_split_ratio else ABTestVariant.B
    
    def _generate_subject(
        self,
        lead: Lead,
        template: EmailTemplate,
        ab_variant: Optional[ABTestVariant] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate email subject line.
        
        Args:
            lead: Lead information
            template: Email template
            ab_variant: A/B test variant
            context: Additional context
            
        Returns:
            Generated subject line
        """
        # Select subject template based on A/B variant
        subject_template = template.subject_template
        if ab_variant == ABTestVariant.B and template.subject_template_b:
            subject_template = template.subject_template_b
        
        # If template is simple, render with Jinja2
        if self._is_simple_template(subject_template):
            return self._render_template(subject_template, lead, context)
        
        # Use OpenAI for complex generation
        return self._generate_with_openai(
            prompt=self._create_subject_prompt(lead, subject_template, context),
            max_tokens=50
        )
    
    def _generate_body(
        self,
        lead: Lead,
        template: EmailTemplate,
        ab_variant: Optional[ABTestVariant] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate email body.
        
        Args:
            lead: Lead information
            template: Email template
            ab_variant: A/B test variant
            context: Additional context
            
        Returns:
            Generated email body
        """
        # Select body template based on A/B variant
        body_template = template.body_template
        if ab_variant == ABTestVariant.B and template.body_template_b:
            body_template = template.body_template_b
        
        # If template is simple, render with Jinja2
        if self._is_simple_template(body_template):
            return self._render_template(body_template, lead, context)
        
        # Use OpenAI for complex generation
        return self._generate_with_openai(
            prompt=self._create_body_prompt(lead, body_template, context),
            max_tokens=500
        )
    
    def _generate_html_body(
        self,
        lead: Lead,
        template: EmailTemplate,
        ab_variant: Optional[ABTestVariant] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Generate HTML email body.
        
        Args:
            lead: Lead information
            template: Email template
            ab_variant: A/B test variant
            context: Additional context
            
        Returns:
            Generated HTML email body or None
        """
        # Select HTML template based on A/B variant
        html_template = template.html_template
        if ab_variant == ABTestVariant.B and template.html_template_b:
            html_template = template.html_template_b
        
        if not html_template:
            return None
        
        # If template is simple, render with Jinja2
        if self._is_simple_template(html_template):
            return self._render_template(html_template, lead, context)
        
        # Use OpenAI for complex generation
        return self._generate_with_openai(
            prompt=self._create_html_prompt(lead, html_template, context),
            max_tokens=800
        )
    
    def _is_simple_template(self, template_text: str) -> bool:
        """Check if template is simple enough for Jinja2 rendering.
        
        Args:
            template_text: Template text to check
            
        Returns:
            True if template is simple, False if needs OpenAI
        """
        # If it contains AI generation instructions, use OpenAI
        ai_keywords = [
            "generate", "create", "personalize", "write",
            "ai:", "gpt:", "assistant:", "please",
            "based on", "considering", "taking into account"
        ]
        
        template_lower = template_text.lower()
        return not any(keyword in template_lower for keyword in ai_keywords)
    
    def _render_template(
        self,
        template_text: str,
        lead: Lead,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Render template using Jinja2.
        
        Args:
            template_text: Template text
            lead: Lead information
            context: Additional context
            
        Returns:
            Rendered template
        """
        try:
            template = Template(template_text)
            
            # Prepare template variables
            variables = lead.to_dict()
            if context:
                variables.update(context)
            
            return template.render(**variables)
            
        except Exception as e:
            logger.error(f"Failed to render template: {e}")
            return template_text
    
    def _create_subject_prompt(
        self,
        lead: Lead,
        template: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create prompt for subject line generation.
        
        Args:
            lead: Lead information
            template: Subject template/instructions
            context: Additional context
            
        Returns:
            Generated prompt
        """
        lead_info = f"""
Lead Information:
- Name: {lead.full_name}
- Email: {lead.email}
- Company: {lead.company}
- Position: {lead.position or 'Not specified'}
- Industry: {lead.industry or 'Not specified'}
- Website: {lead.website or 'Not specified'}
- Location: {lead.location or 'Not specified'}
"""
        
        if context:
            context_str = "\nAdditional Context:\n" + "\n".join([f"- {k}: {v}" for k, v in context.items()])
            lead_info += context_str
        
        return f"""
{lead_info}

Instructions: {template}

Generate a personalized email subject line for this lead. The subject should be:
- Compelling and attention-grabbing
- Personalized based on the lead information
- Professional and relevant to their role/industry
- Not spammy or overly salesy
- Maximum 60 characters

Subject line:"""
    
    def _create_body_prompt(
        self,
        lead: Lead,
        template: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create prompt for email body generation.
        
        Args:
            lead: Lead information
            template: Body template/instructions
            context: Additional context
            
        Returns:
            Generated prompt
        """
        lead_info = f"""
Lead Information:
- Name: {lead.full_name}
- Email: {lead.email}
- Company: {lead.company}
- Position: {lead.position or 'Not specified'}
- Industry: {lead.industry or 'Not specified'}
- Website: {lead.website or 'Not specified'}
- Location: {lead.location or 'Not specified'}
"""
        
        if context:
            context_str = "\nAdditional Context:\n" + "\n".join([f"- {k}: {v}" for k, v in context.items()])
            lead_info += context_str
        
        return f"""
{lead_info}

Instructions: {template}

Generate a personalized email body for this lead. The email should be:
- Professional and well-structured
- Personalized based on the lead information
- Clear and concise
- Include a compelling call-to-action
- Appropriate for business communication
- 2-4 paragraphs in length

Email body:"""
    
    def _create_html_prompt(
        self,
        lead: Lead,
        template: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create prompt for HTML email generation.
        
        Args:
            lead: Lead information
            template: HTML template/instructions
            context: Additional context
            
        Returns:
            Generated prompt
        """
        lead_info = f"""
Lead Information:
- Name: {lead.full_name}
- Email: {lead.email}
- Company: {lead.company}
- Position: {lead.position or 'Not specified'}
- Industry: {lead.industry or 'Not specified'}
- Website: {lead.website or 'Not specified'}
- Location: {lead.location or 'Not specified'}
"""
        
        if context:
            context_str = "\nAdditional Context:\n" + "\n".join([f"- {k}: {v}" for k, v in context.items()])
            lead_info += context_str
        
        return f"""
{lead_info}

Instructions: {template}

Generate HTML email content for this lead. The HTML should be:
- Clean and responsive
- Professional looking
- Include proper styling
- Personalized based on lead information
- Compatible with email clients

HTML content:"""
    
    def _generate_with_openai(self, prompt: str, max_tokens: int = 200) -> str:
        """Generate content using OpenAI API.
        
        Args:
            prompt: Generation prompt
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated content
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional email marketing assistant that creates personalized, engaging business emails."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    def generate_batch(
        self,
        leads: List[Lead],
        template: EmailTemplate,
        context: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[callable] = None
    ) -> List[GeneratedEmail]:
        """Generate emails for a batch of leads.
        
        Args:
            leads: List of leads
            template: Email template
            context: Additional context
            progress_callback: Optional progress callback function
            
        Returns:
            List of generated emails
        """
        logger.info(f"Starting batch generation for {len(leads)} leads")
        
        emails = []
        for i, lead in enumerate(leads):
            try:
                email = self.generate_email(lead, template, context)
                emails.append(email)
                
                if progress_callback:
                    progress_callback(i + 1, len(leads), email)
                
                # Small delay to avoid rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Failed to generate email for lead {i+1}: {e}")
                
                # Create failed email
                failed_email = GeneratedEmail(
                    lead=lead,
                    template_name=template.name,
                    subject="",
                    body="",
                )
                failed_email.mark_failed(str(e))
                emails.append(failed_email)
        
        logger.info(f"Completed batch generation: {len(emails)} emails generated")
        return emails