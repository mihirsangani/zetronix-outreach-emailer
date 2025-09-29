"""Test configuration for pytest."""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch
from zetronix_emailer.models import Lead, EmailTemplate, GeneratedEmail


@pytest.fixture
def sample_lead():
    """Sample lead for testing."""
    return Lead(
        email="john.doe@example.com",
        first_name="John",
        last_name="Doe",
        company="Example Corp",
        position="CEO",
        industry="Technology",
        website="https://example.com",
        location="San Francisco, CA"
    )


@pytest.fixture
def sample_template():
    """Sample email template for testing."""
    return EmailTemplate(
        name="Test Template",
        subject_template="Hello {{first_name}}!",
        body_template="Hi {{first_name}}, I hope you're doing well at {{company}}.",
        html_template="<p>Hi {{first_name}}, I hope you're doing well at {{company}}.</p>",
        ab_test_enabled=True,
        subject_template_b="{{first_name}}, quick question",
        body_template_b="Hello {{first_name}}, I have a quick question about {{company}}."
    )


@pytest.fixture
def sample_generated_email(sample_lead, sample_template):
    """Sample generated email for testing."""
    return GeneratedEmail(
        lead=sample_lead,
        template_name=sample_template.name,
        subject="Hello John!",
        body="Hi John, I hope you're doing well at Example Corp.",
        html_body="<p>Hi John, I hope you're doing well at Example Corp.</p>"
    )


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    with patch('zetronix_emailer.config.config') as mock_config:
        mock_config.openai_api_key = "test-key"
        mock_config.openai_model = "gpt-4"
        mock_config.google_spreadsheet_id = "test-sheet-id"
        mock_config.smtp_server = "smtp.test.com"
        mock_config.smtp_username = "test@test.com"
        mock_config.smtp_password = "test-password"
        mock_config.ab_test_enabled = True
        mock_config.ab_test_split_ratio = 0.5
        mock_config.log_level = "INFO"
        yield mock_config


@pytest.fixture
def temp_dir():
    """Temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir