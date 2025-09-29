# Zetronix Outreach Emailer

AI-powered outreach email generator that reads leads from Google Sheets, creates personalized emails using OpenAI, and optionally sends them via SMTP. Features clean code architecture, comprehensive logging, error handling, HTML email support, and A/B subject testing.

## Features

🤖 **AI-Powered Email Generation** - Uses OpenAI GPT models to create personalized emails
📊 **Google Sheets Integration** - Reads leads and writes results to Google Sheets
📧 **SMTP Email Sending** - Optional email sending with HTML support
🧪 **A/B Testing** - Built-in A/B testing for subject lines and content
📝 **Template System** - Flexible Jinja2 templates with AI enhancement
🔍 **Comprehensive Logging** - Detailed logging with colored console output
⚡ **Error Handling** - Robust error handling and recovery
🎯 **Campaign Management** - Complete campaign workflow automation
🛠️ **CLI Interface** - Easy-to-use command line interface

## Installation

```bash
# Clone the repository
git clone https://github.com/mihirsangani/zetronix-outreach-emailer.git
cd zetronix-outreach-emailer

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

## Configuration

1. **Copy the environment template:**
```bash
cp .env.example .env
```

2. **Configure your settings in `.env`:**

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4

# Google Sheets Configuration
GOOGLE_CREDENTIALS_PATH=path/to/your/google-credentials.json
GOOGLE_SPREADSHEET_ID=your_google_spreadsheet_id

# SMTP Configuration (Optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_USE_TLS=true

# A/B Testing Configuration
AB_TEST_ENABLED=true
AB_TEST_SPLIT_RATIO=0.5
```

## Google Sheets Setup

### 1. Create Google Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google Sheets API and Google Drive API
4. Create a service account and download JSON credentials
5. Share your Google Sheet with the service account email

### 2. Prepare Your Leads Sheet

Your Google Sheet should have a "Leads" worksheet with these columns:

| email | first_name | last_name | company | position | industry | website | phone | location | notes |
|-------|------------|-----------|---------|----------|----------|---------|-------|----------|-------|
| john@example.com | John | Doe | Example Corp | CEO | Technology | example.com | +1234567890 | San Francisco | VIP lead |

### 3. Results Sheet

The system will automatically create a "Results" sheet with campaign results.

## Usage

### CLI Commands

#### 1. Test Configuration
```bash
zetronix-emailer test
```

#### 2. Create Email Template
```bash
zetronix-emailer create-template -o my_template.json
```

#### 3. Preview Emails
```bash
zetronix-emailer preview -t my_template.json -n 5
```

#### 4. Run Campaign (Preview Only)
```bash
zetronix-emailer run -t my_template.json --no-send
```

#### 5. Run Campaign with Email Sending
```bash
zetronix-emailer run -t my_template.json --send --from-email "you@company.com" --from-name "Your Name"
```

#### 6. Dry Run (Test Email Generation and Sending Logic)
```bash
zetronix-emailer run -t my_template.json --send --dry-run
```

### Email Templates

Create JSON template files with this structure:

```json
{
  "name": "Professional Outreach",
  "subject_template": "Quick question about {{company}}",
  "body_template": "Hi {{first_name}},\n\nI hope this email finds you well. I noticed your work at {{company}} and was impressed by your {{industry}} innovations.\n\nI'd love to discuss how we might collaborate.\n\nBest regards",
  "html_template": "<p>Hi {{first_name}},</p><p>I hope this email finds you well...</p>",
  "is_active": true,
  "ab_test_enabled": true,
  "subject_template_b": "{{first_name}}, partnership opportunity at {{company}}",
  "body_template_b": "Hello {{first_name}},\n\nYour work at {{company}} caught my attention, especially in the {{industry}} space.\n\nI believe there's a great partnership opportunity here. Could we schedule a brief call?\n\nLooking forward to hearing from you"
}
```

### AI-Enhanced Templates

For more sophisticated email generation, use AI instructions in your templates:

```json
{
  "name": "AI Enhanced Outreach",
  "subject_template": "Generate a compelling subject line for {{first_name}} at {{company}} in the {{industry}} industry. Make it personal and professional.",
  "body_template": "Create a personalized outreach email for {{first_name}} who works at {{company}} in {{position}}. The email should:\n- Be professional and engaging\n- Reference their industry ({{industry}})\n- Propose a collaboration\n- Include a clear call-to-action\n- Be 2-3 paragraphs long"
}
```

### Python API

Use the library programmatically:

```python
from zetronix_emailer import OutreachCampaign, EmailTemplate, GoogleSheetsClient
from zetronix_emailer.models import Lead

# Initialize campaign
campaign = OutreachCampaign()

# Create template
template = EmailTemplate(
    name="My Campaign",
    subject_template="Hello {{first_name}}!",
    body_template="Hi {{first_name}}, I hope {{company}} is doing well!"
)

# Run campaign
stats = campaign.run_campaign(
    template=template,
    send_emails=True,
    from_email="you@company.com",
    from_name="Your Name"
)

print(f"Sent {stats.emails_sent} emails with {stats.success_rate:.1f}% success rate")
```

## A/B Testing

The system supports A/B testing for subject lines and email content:

1. **Enable A/B Testing** in your template:
```json
{
  "ab_test_enabled": true,
  "subject_template": "Version A subject",
  "subject_template_b": "Version B subject",
  "body_template": "Version A body",
  "body_template_b": "Version B body"
}
```

2. **Configure Split Ratio** in `.env`:
```bash
AB_TEST_SPLIT_RATIO=0.5  # 50/50 split
```

3. **View Results** in the Results sheet with A/B variant tracking.

## Logging

The system provides comprehensive logging:

- **Console Output**: Colored, timestamped logs
- **File Logging**: Detailed logs saved to file
- **Progress Tracking**: Real-time campaign progress
- **Error Details**: Comprehensive error information

Configure logging in `.env`:
```bash
LOG_LEVEL=INFO
LOG_FILE=emailer.log
```

## Error Handling

Robust error handling includes:

- **API Failures**: OpenAI and Google Sheets API errors
- **SMTP Issues**: Email sending failures with retry logic
- **Data Validation**: Lead and template validation
- **Graceful Degradation**: Continues processing on individual failures
- **Detailed Error Reporting**: Error tracking in results

## Best Practices

### 1. Email Deliverability
- Use authenticated SMTP servers
- Configure SPF, DKIM, and DMARC records
- Start with small batches to build reputation
- Monitor bounce rates and spam complaints

### 2. Personalization
- Include dynamic fields ({{first_name}}, {{company}})
- Use AI templates for context-aware generation
- Add custom fields for additional personalization
- Test different personalization approaches

### 3. Compliance
- Include unsubscribe links
- Respect opt-out requests
- Follow CAN-SPAM and GDPR guidelines
- Maintain consent records

### 4. Performance
- Use rate limiting to avoid API limits
- Monitor generation and sending times
- Batch process large campaigns
- Handle failures gracefully

## Development

### Running Tests
```bash
pytest tests/ -v
```

### Code Quality
```bash
# Format code
black zetronix_emailer/

# Lint code
flake8 zetronix_emailer/

# Type checking
mypy zetronix_emailer/
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Troubleshooting

### Common Issues

**OpenAI API Errors**
- Check API key validity
- Verify billing and usage limits
- Monitor rate limits

**Google Sheets Access**
- Verify service account credentials
- Check sheet sharing permissions
- Ensure APIs are enabled

**SMTP Issues**
- Test connection with `zetronix-emailer test-email`
- Check authentication credentials
- Verify server settings and ports

**Template Errors**
- Validate JSON syntax
- Check required fields
- Test with preview command

## License

MIT License - see LICENSE file for details.

## Support

For support, please:
1. Check the troubleshooting section
2. Review logs for error details
3. Create an issue on GitHub
4. Provide configuration (without sensitive data) and error logs
