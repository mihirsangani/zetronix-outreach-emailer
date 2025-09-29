"""Tests for OpenAI email generator."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from zetronix_emailer.openai_client import OpenAIEmailGenerator
from zetronix_emailer.models import Lead, EmailTemplate, EmailStatus, ABTestVariant


@pytest.fixture
def mock_openai():
    """Mock OpenAI API."""
    with patch('zetronix_emailer.openai_client.openai') as mock_openai:
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Generated email content"
        mock_openai.ChatCompletion.create.return_value = mock_response
        yield mock_openai


def test_generator_initialization(mock_config):
    """Test OpenAI generator initialization."""
    generator = OpenAIEmailGenerator()
    assert generator.api_key == "test-key"
    assert generator.model == "gpt-4"


def test_simple_template_detection():
    """Test simple template detection."""
    generator = OpenAIEmailGenerator()
    
    # Simple template
    simple = "Hello {{first_name}}, welcome to {{company}}!"
    assert generator._is_simple_template(simple) is True
    
    # Complex template requiring AI
    complex_template = "Generate a personalized email for {{first_name}} based on their company {{company}}"
    assert generator._is_simple_template(complex_template) is False


def test_template_rendering(sample_lead):
    """Test Jinja2 template rendering."""
    generator = OpenAIEmailGenerator()
    
    template = "Hello {{first_name}}, I hope {{company}} is doing well!"
    result = generator._render_template(template, sample_lead)
    
    assert "Hello John" in result
    assert "Example Corp" in result


def test_ab_variant_determination(mock_config):
    """Test A/B variant determination."""
    generator = OpenAIEmailGenerator()
    
    # Run multiple times to test randomness
    variants = []
    for _ in range(100):
        variant = generator._determine_ab_variant()
        variants.append(variant)
    
    # Should have both A and B variants
    assert ABTestVariant.A in variants
    assert ABTestVariant.B in variants


@patch('zetronix_emailer.openai_client.openai')
def test_generate_email_simple_template(mock_openai, sample_lead, mock_config):
    """Test email generation with simple template."""
    generator = OpenAIEmailGenerator()
    
    template = EmailTemplate(
        name="Simple Template",
        subject_template="Hello {{first_name}}!",
        body_template="Hi {{first_name}}, welcome to our service."
    )
    
    email = generator.generate_email(sample_lead, template)
    
    assert email.status == EmailStatus.GENERATED
    assert email.subject == "Hello John!"
    assert "Hi John" in email.body
    
    # Simple template shouldn't call OpenAI
    mock_openai.ChatCompletion.create.assert_not_called()


@patch('zetronix_emailer.openai_client.openai')
def test_generate_email_complex_template(mock_openai, sample_lead, mock_config):
    """Test email generation with complex template requiring AI."""
    # Mock OpenAI response
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "AI generated content"
    mock_openai.ChatCompletion.create.return_value = mock_response
    
    generator = OpenAIEmailGenerator()
    
    template = EmailTemplate(
        name="Complex Template",
        subject_template="Generate a personalized subject for {{first_name}}",
        body_template="Create a personalized email for {{first_name}} at {{company}}"
    )
    
    email = generator.generate_email(sample_lead, template)
    
    assert email.status == EmailStatus.GENERATED
    assert email.subject == "AI generated content"
    assert email.body == "AI generated content"
    
    # Should call OpenAI for both subject and body
    assert mock_openai.ChatCompletion.create.call_count == 2


@patch('zetronix_emailer.openai_client.openai')
def test_generate_email_with_ab_testing(mock_openai, sample_lead, mock_config):
    """Test email generation with A/B testing."""
    # Mock OpenAI response
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "AI generated content"
    mock_openai.ChatCompletion.create.return_value = mock_response
    
    generator = OpenAIEmailGenerator()
    
    template = EmailTemplate(
        name="A/B Template",
        subject_template="Version A: {{first_name}}",
        body_template="Version A body",
        ab_test_enabled=True,
        subject_template_b="Version B: {{first_name}}",
        body_template_b="Version B body"
    )
    
    email = generator.generate_email(sample_lead, template)
    
    assert email.status == EmailStatus.GENERATED
    assert email.ab_variant in [ABTestVariant.A, ABTestVariant.B]
    
    # Should use either A or B variant
    if email.ab_variant == ABTestVariant.A:
        assert "Version A" in email.subject or email.subject == "AI generated content"
    else:
        assert "Version B" in email.subject or email.subject == "AI generated content"


@patch('zetronix_emailer.openai_client.openai')
def test_generate_batch(mock_openai, mock_config):
    """Test batch email generation."""
    # Mock OpenAI response
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "AI generated content"
    mock_openai.ChatCompletion.create.return_value = mock_response
    
    generator = OpenAIEmailGenerator()
    
    leads = [
        Lead(email="user1@example.com", first_name="User1", last_name="Test", company="Corp1"),
        Lead(email="user2@example.com", first_name="User2", last_name="Test", company="Corp2"),
    ]
    
    template = EmailTemplate(
        name="Batch Template",
        subject_template="Hello {{first_name}}!",
        body_template="Hi {{first_name}}"
    )
    
    progress_calls = []
    def progress_callback(current, total, email):
        progress_calls.append((current, total, email.lead.email))
    
    emails = generator.generate_batch(leads, template, progress_callback=progress_callback)
    
    assert len(emails) == 2
    assert all(email.status == EmailStatus.GENERATED for email in emails)
    assert len(progress_calls) == 2


@patch('zetronix_emailer.openai_client.openai')
def test_openai_api_error_handling(mock_openai, sample_lead, mock_config):
    """Test OpenAI API error handling."""
    # Mock OpenAI to raise an exception
    mock_openai.ChatCompletion.create.side_effect = Exception("API Error")
    
    generator = OpenAIEmailGenerator()
    
    template = EmailTemplate(
        name="Error Template",
        subject_template="Generate subject for {{first_name}}",
        body_template="Generate body for {{first_name}}"
    )
    
    email = generator.generate_email(sample_lead, template)
    
    assert email.status == EmailStatus.FAILED
    assert "API Error" in email.error_message