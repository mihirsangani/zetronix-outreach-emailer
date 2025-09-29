"""Command line interface for Zetronix Outreach Emailer."""

import click
import json
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from .models import EmailTemplate, ABTestVariant
from .campaign import OutreachCampaign
from .sheets_client import GoogleSheetsClient
from .openai_client import OpenAIEmailGenerator
from .email_sender import SMTPEmailSender
from .logging_utils import get_logger, setup_logger
from .config import config

logger = get_logger(__name__)


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--log-file', help='Log file path')
def cli(verbose, log_file):
    """Zetronix Outreach Emailer - AI-powered email generation and outreach automation."""
    log_level = 'DEBUG' if verbose else config.log_level
    setup_logger('zetronix_emailer', log_level, log_file)


@cli.command()
@click.option('--template-file', '-t', required=True, help='Path to email template JSON file')
@click.option('--leads-sheet', help='Name of Google Sheets leads worksheet')
@click.option('--results-sheet', help='Name of Google Sheets results worksheet')
@click.option('--send/--no-send', default=False, help='Whether to send emails via SMTP')
@click.option('--dry-run', is_flag=True, help='Perform dry run without actually sending emails')
@click.option('--from-email', help='Sender email address')
@click.option('--from-name', help='Sender display name')
@click.option('--reply-to', help='Reply-to email address')
@click.option('--context-file', help='Path to JSON file with additional context')
def run(template_file, leads_sheet, results_sheet, send, dry_run, 
        from_email, from_name, reply_to, context_file):
    """Run outreach campaign."""
    try:
        # Load template
        template = load_template(template_file)
        
        # Load context
        context = None
        if context_file:
            with open(context_file, 'r') as f:
                context = json.load(f)
        
        # Initialize campaign
        campaign = OutreachCampaign()
        
        # Progress callback
        def progress_callback(message):
            click.echo(f"📧 {message}")
        
        # Run campaign
        click.echo("🚀 Starting outreach campaign...")
        
        stats = campaign.run_campaign(
            template=template,
            leads_sheet=leads_sheet,
            results_sheet=results_sheet,
            send_emails=send,
            dry_run=dry_run,
            from_email=from_email,
            from_name=from_name,
            reply_to=reply_to,
            context=context,
            progress_callback=progress_callback
        )
        
        # Display results
        click.echo("\n📊 Campaign Results:")
        click.echo(f"   Total Leads: {stats.total_leads}")
        click.echo(f"   Emails Generated: {stats.emails_generated}")
        click.echo(f"   Emails Sent: {stats.emails_sent}")
        click.echo(f"   Emails Failed: {stats.emails_failed}")
        click.echo(f"   Success Rate: {stats.success_rate:.1f}%")
        
        if stats.variant_a_sent > 0 or stats.variant_b_sent > 0:
            click.echo(f"   A/B Test - Variant A: {stats.variant_a_sent}")
            click.echo(f"   A/B Test - Variant B: {stats.variant_b_sent}")
        
        click.echo("\n✅ Campaign completed successfully!")
        
    except Exception as e:
        click.echo(f"❌ Campaign failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--template-file', '-t', required=True, help='Path to email template JSON file')
@click.option('--leads-sheet', help='Name of Google Sheets leads worksheet')
@click.option('--max-previews', '-n', default=5, help='Maximum number of previews to generate')
@click.option('--context-file', help='Path to JSON file with additional context')
@click.option('--output-file', '-o', help='Save previews to JSON file')
def preview(template_file, leads_sheet, max_previews, context_file, output_file):
    """Preview generated emails without sending."""
    try:
        # Load template
        template = load_template(template_file)
        
        # Load context
        context = None
        if context_file:
            with open(context_file, 'r') as f:
                context = json.load(f)
        
        # Initialize campaign
        campaign = OutreachCampaign()
        
        click.echo(f"🔍 Generating {max_previews} email previews...")
        
        # Generate previews
        previews = campaign.preview_emails(
            template=template,
            leads_sheet=leads_sheet,
            max_previews=max_previews,
            context=context
        )
        
        # Display previews
        for i, email in enumerate(previews, 1):
            click.echo(f"\n📧 Preview {i} - {email.lead.email}")
            click.echo(f"   Subject: {email.subject}")
            click.echo(f"   Status: {email.status.value}")
            if email.ab_variant:
                click.echo(f"   A/B Variant: {email.ab_variant.value}")
            
            click.echo("   Body:")
            body_lines = email.body.split('\n')
            for line in body_lines[:10]:  # Show first 10 lines
                click.echo(f"   {line}")
            if len(body_lines) > 10:
                click.echo("   ...")
        
        # Save to file if requested
        if output_file:
            preview_data = []
            for email in previews:
                preview_data.append({
                    'lead': email.lead.dict(),
                    'subject': email.subject,
                    'body': email.body,
                    'html_body': email.html_body,
                    'status': email.status.value,
                    'ab_variant': email.ab_variant.value if email.ab_variant else None,
                    'generated_at': email.generated_at.isoformat()
                })
            
            with open(output_file, 'w') as f:
                json.dump(preview_data, f, indent=2)
            
            click.echo(f"\n💾 Previews saved to {output_file}")
        
        click.echo(f"\n✅ Generated {len(previews)} previews successfully!")
        
    except Exception as e:
        click.echo(f"❌ Preview generation failed: {e}", err=True)
        sys.exit(1)


@cli.command()
def test():
    """Test all integrations."""
    try:
        click.echo("🔧 Testing integrations...")
        
        # Initialize campaign
        campaign = OutreachCampaign()
        
        # Run tests
        results = campaign.test_integrations()
        
        # Display results
        click.echo("\n📊 Test Results:")
        for service, success in results.items():
            status = "✅" if success else "❌"
            click.echo(f"   {service.replace('_', ' ').title()}: {status}")
        
        # Overall result
        if all(results.values()):
            click.echo("\n✅ All integrations working correctly!")
        else:
            click.echo("\n⚠️  Some integrations need configuration.")
            click.echo("Please check your .env file and credentials.")
        
    except Exception as e:
        click.echo(f"❌ Integration test failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--to-email', required=True, help='Email address to send test email to')
@click.option('--from-email', help='Sender email address')
@click.option('--from-name', help='Sender display name')
def test_email(to_email, from_email, from_name):
    """Send a test email."""
    try:
        click.echo(f"📧 Sending test email to {to_email}...")
        
        sender = SMTPEmailSender()
        success = sender.send_test_email(to_email, from_email, from_name)
        
        if success:
            click.echo("✅ Test email sent successfully!")
        else:
            click.echo("❌ Failed to send test email.")
            sys.exit(1)
        
    except Exception as e:
        click.echo(f"❌ Test email failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--output-file', '-o', default='email_template.json', help='Output template file')
def create_template(output_file):
    """Create a sample email template."""
    try:
        # Sample template
        template_data = {
            "name": "Professional Outreach",
            "subject_template": "Quick question about {{company}}",
            "body_template": "Hi {{first_name}},\n\nI hope this email finds you well. I noticed your work at {{company}} and was impressed by {{industry}} innovations.\n\nI'd love to discuss how we might collaborate.\n\nBest regards",
            "html_template": None,
            "is_active": True,
            "ab_test_enabled": True,
            "subject_template_b": "{{first_name}}, partnership opportunity at {{company}}",
            "body_template_b": "Hello {{first_name}},\n\nYour work at {{company}} caught my attention, especially in the {{industry}} space.\n\nI believe there's a great partnership opportunity here. Could we schedule a brief call?\n\nLooking forward to hearing from you",
            "html_template_b": None
        }
        
        with open(output_file, 'w') as f:
            json.dump(template_data, f, indent=2)
        
        click.echo(f"📄 Sample template created: {output_file}")
        click.echo("You can edit this file to customize your email template.")
        
    except Exception as e:
        click.echo(f"❌ Failed to create template: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--leads-sheet', help='Name of Google Sheets leads worksheet')
def show_leads(leads_sheet):
    """Show leads from Google Sheets."""
    try:
        click.echo("📋 Reading leads from Google Sheets...")
        
        sheets_client = GoogleSheetsClient()
        leads = sheets_client.read_leads(leads_sheet)
        
        if not leads:
            click.echo("No leads found.")
            return
        
        click.echo(f"\n📊 Found {len(leads)} leads:")
        
        for i, lead in enumerate(leads[:10], 1):  # Show first 10
            click.echo(f"   {i}. {lead.full_name} ({lead.email}) - {lead.company}")
        
        if len(leads) > 10:
            click.echo(f"   ... and {len(leads) - 10} more")
        
    except Exception as e:
        click.echo(f"❌ Failed to read leads: {e}", err=True)
        sys.exit(1)


@cli.command()
def info():
    """Show configuration information."""
    try:
        click.echo("ℹ️  Zetronix Outreach Emailer Configuration:")
        click.echo(f"   OpenAI Model: {config.openai_model}")
        click.echo(f"   Google Spreadsheet ID: {config.google_spreadsheet_id[:20]}...")
        click.echo(f"   SMTP Server: {config.smtp_server or 'Not configured'}")
        click.echo(f"   A/B Testing: {'Enabled' if config.ab_test_enabled else 'Disabled'}")
        click.echo(f"   Log Level: {config.log_level}")
        click.echo(f"   Log File: {config.log_file}")
        
        # Show sheet info
        try:
            sheets_client = GoogleSheetsClient()
            sheet_info = sheets_client.get_sheet_info()
            if sheet_info:
                click.echo(f"\n📊 Google Sheets Info:")
                click.echo(f"   Title: {sheet_info.get('title', 'Unknown')}")
                click.echo(f"   Worksheets: {', '.join(sheet_info.get('worksheets', []))}")
        except:
            pass
        
    except Exception as e:
        click.echo(f"❌ Failed to show info: {e}", err=True)


def load_template(template_file: str) -> EmailTemplate:
    """Load email template from JSON file.
    
    Args:
        template_file: Path to template JSON file
        
    Returns:
        Email template object
    """
    try:
        with open(template_file, 'r') as f:
            data = json.load(f)
        
        return EmailTemplate(**data)
        
    except Exception as e:
        raise click.ClickException(f"Failed to load template from {template_file}: {e}")


def main():
    """Main CLI entry point."""
    cli()


if __name__ == '__main__':
    main()