"""Tests for data models."""

import pytest
from datetime import datetime
from zetronix_emailer.models import Lead, EmailTemplate, GeneratedEmail, EmailStatus, ABTestVariant


def test_lead_creation():
    """Test lead creation and validation."""
    lead = Lead(
        email="john.doe@example.com",
        first_name="John",
        last_name="Doe",
        company="Example Corp"
    )
    
    assert lead.email == "john.doe@example.com"
    assert lead.first_name == "John"
    assert lead.last_name == "Doe"
    assert lead.company == "Example Corp"
    assert lead.full_name == "John Doe"


def test_lead_to_dict():
    """Test lead to dictionary conversion."""
    lead = Lead(
        email="john.doe@example.com",
        first_name="John",
        last_name="Doe",
        company="Example Corp",
        position="CEO"
    )
    
    data = lead.to_dict()
    assert data['email'] == "john.doe@example.com"
    assert data['full_name'] == "John Doe"
    assert data['position'] == "CEO"


def test_email_template_creation():
    """Test email template creation."""
    template = EmailTemplate(
        name="Test Template",
        subject_template="Hello {{first_name}}!",
        body_template="Hi {{first_name}}, how are you?"
    )
    
    assert template.name == "Test Template"
    assert template.subject_template == "Hello {{first_name}}!"
    assert template.is_active is True


def test_generated_email_status():
    """Test generated email status management."""
    lead = Lead(
        email="test@example.com",
        first_name="Test",
        last_name="User",
        company="Test Corp"
    )
    
    email = GeneratedEmail(
        lead=lead,
        template_name="Test Template",
        subject="Test Subject",
        body="Test Body"
    )
    
    assert email.status == EmailStatus.GENERATED
    assert email.sent_at is None
    
    # Mark as sent
    email.mark_sent()
    assert email.status == EmailStatus.SENT
    assert email.sent_at is not None
    
    # Mark as failed
    email.mark_failed("SMTP error")
    assert email.status == EmailStatus.FAILED
    assert email.error_message == "SMTP error"


def test_ab_variant_enum():
    """Test A/B variant enumeration."""
    assert ABTestVariant.A == "A"
    assert ABTestVariant.B == "B"


def test_lead_custom_fields():
    """Test lead custom fields handling."""
    lead = Lead(
        email="test@example.com",
        first_name="Test",
        last_name="User",
        company="Test Corp",
        custom_fields={"linkedin": "https://linkedin.com/in/testuser", "score": 85}
    )
    
    assert lead.custom_fields["linkedin"] == "https://linkedin.com/in/testuser"
    assert lead.custom_fields["score"] == 85