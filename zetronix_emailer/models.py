"""Data models for the Zetronix Outreach Emailer."""

from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
try:
    from pydantic import BaseModel, validator, EmailStr
except ImportError:
    # Fallback for older pydantic versions or missing email-validator
    from pydantic import BaseModel, validator
    EmailStr = str


class EmailStatus(str, Enum):
    """Email status enumeration."""
    PENDING = "pending"
    GENERATED = "generated"
    SENT = "sent"
    FAILED = "failed"


class ABTestVariant(str, Enum):
    """A/B test variant enumeration."""
    A = "A"
    B = "B"


class Lead(BaseModel):
    """Lead data model."""
    
    # Required fields
    email: EmailStr
    first_name: str
    last_name: str
    company: str
    
    # Optional fields
    position: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    
    # Additional custom fields
    custom_fields: Dict[str, Any] = {}
    
    @property
    def full_name(self) -> str:
        """Get full name of the lead."""
        return f"{self.first_name} {self.last_name}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert lead to dictionary for template rendering."""
        data = self.dict()
        data['full_name'] = self.full_name
        return data


class EmailTemplate(BaseModel):
    """Email template model."""
    
    name: str
    subject_template: str
    body_template: str
    html_template: Optional[str] = None
    is_active: bool = True
    created_at: datetime = datetime.now()
    
    # A/B Testing support
    ab_test_enabled: bool = False
    subject_template_b: Optional[str] = None
    body_template_b: Optional[str] = None
    html_template_b: Optional[str] = None


class GeneratedEmail(BaseModel):
    """Generated email model."""
    
    lead: Lead
    template_name: str
    subject: str
    body: str
    html_body: Optional[str] = None
    
    # A/B Testing
    ab_variant: Optional[ABTestVariant] = None
    
    # Status tracking
    status: EmailStatus = EmailStatus.GENERATED
    generated_at: datetime = datetime.now()
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    # Metadata
    openai_model_used: Optional[str] = None
    generation_time_ms: Optional[int] = None
    
    def mark_sent(self):
        """Mark email as sent."""
        self.status = EmailStatus.SENT
        self.sent_at = datetime.now()
    
    def mark_failed(self, error: str):
        """Mark email as failed."""
        self.status = EmailStatus.FAILED
        self.error_message = error


class CampaignStats(BaseModel):
    """Campaign statistics model."""
    
    total_leads: int = 0
    emails_generated: int = 0
    emails_sent: int = 0
    emails_failed: int = 0
    
    # A/B Testing stats
    variant_a_sent: int = 0
    variant_b_sent: int = 0
    
    start_time: datetime = datetime.now()
    end_time: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate email success rate."""
        if self.emails_generated == 0:
            return 0.0
        return (self.emails_sent / self.emails_generated) * 100
    
    @property
    def failure_rate(self) -> float:
        """Calculate email failure rate."""
        if self.emails_generated == 0:
            return 0.0
        return (self.emails_failed / self.emails_generated) * 100


class SheetConfig(BaseModel):
    """Google Sheets configuration model."""
    
    # Sheet names/ranges
    leads_sheet: str = "Leads"
    results_sheet: str = "Results"
    
    # Column mappings for leads sheet
    email_column: str = "email"
    first_name_column: str = "first_name"
    last_name_column: str = "last_name"
    company_column: str = "company"
    position_column: str = "position"
    industry_column: str = "industry"
    website_column: str = "website"
    phone_column: str = "phone"
    location_column: str = "location"
    notes_column: str = "notes"
    
    # Column mappings for results sheet
    status_column: str = "status"
    generated_at_column: str = "generated_at"
    sent_at_column: str = "sent_at"
    subject_column: str = "subject"
    body_column: str = "body"
    error_column: str = "error_message"
    ab_variant_column: str = "ab_variant"