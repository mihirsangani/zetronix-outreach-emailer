"""Google Sheets integration for reading leads and writing results."""

import gspread
from typing import List, Dict, Any, Optional
from google.oauth2.service_account import Credentials
from oauth2client.service_account import ServiceAccountCredentials
from .models import Lead, GeneratedEmail, SheetConfig
from .logging_utils import get_logger
from .config import config

logger = get_logger(__name__)


class GoogleSheetsClient:
    """Google Sheets client for lead management and results tracking."""
    
    def __init__(self, credentials_path: Optional[str] = None, spreadsheet_id: Optional[str] = None):
        """Initialize Google Sheets client.
        
        Args:
            credentials_path: Path to Google service account credentials JSON
            spreadsheet_id: Google Spreadsheet ID
        """
        self.credentials_path = credentials_path or config.google_credentials_path
        self.spreadsheet_id = spreadsheet_id or config.google_spreadsheet_id
        self.sheet_config = SheetConfig()
        
        # Authentication scope
        self.scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        self.client = None
        self.spreadsheet = None
        
        if self.credentials_path:
            self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Sheets API."""
        try:
            logger.info("Authenticating with Google Sheets API...")
            
            # Use service account credentials
            creds = ServiceAccountCredentials.from_json_keyfile_name(
                self.credentials_path, self.scope
            )
            self.client = gspread.authorize(creds)
            
            # Open the spreadsheet
            self.spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            
            logger.info("Successfully authenticated with Google Sheets")
            
        except Exception as e:
            logger.error(f"Failed to authenticate with Google Sheets: {e}")
            raise
    
    def _get_worksheet(self, sheet_name: str):
        """Get or create a worksheet.
        
        Args:
            sheet_name: Name of the worksheet
            
        Returns:
            Worksheet instance
        """
        try:
            return self.spreadsheet.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            logger.info(f"Creating worksheet: {sheet_name}")
            return self.spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
    
    def read_leads(self, sheet_name: Optional[str] = None) -> List[Lead]:
        """Read leads from Google Sheets.
        
        Args:
            sheet_name: Name of the leads sheet
            
        Returns:
            List of Lead objects
        """
        if not self.client:
            raise ValueError("Google Sheets client not authenticated")
        
        sheet_name = sheet_name or self.sheet_config.leads_sheet
        
        try:
            logger.info(f"Reading leads from sheet: {sheet_name}")
            
            worksheet = self._get_worksheet(sheet_name)
            records = worksheet.get_all_records()
            
            leads = []
            for record in records:
                try:
                    # Map sheet columns to Lead model fields
                    lead_data = {
                        'email': record.get(self.sheet_config.email_column, ''),
                        'first_name': record.get(self.sheet_config.first_name_column, ''),
                        'last_name': record.get(self.sheet_config.last_name_column, ''),
                        'company': record.get(self.sheet_config.company_column, ''),
                        'position': record.get(self.sheet_config.position_column),
                        'industry': record.get(self.sheet_config.industry_column),
                        'website': record.get(self.sheet_config.website_column),
                        'phone': record.get(self.sheet_config.phone_column),
                        'location': record.get(self.sheet_config.location_column),
                        'notes': record.get(self.sheet_config.notes_column),
                    }
                    
                    # Remove empty values
                    lead_data = {k: v for k, v in lead_data.items() if v}
                    
                    # Add custom fields
                    custom_fields = {}
                    for key, value in record.items():
                        if key not in [
                            self.sheet_config.email_column,
                            self.sheet_config.first_name_column,
                            self.sheet_config.last_name_column,
                            self.sheet_config.company_column,
                            self.sheet_config.position_column,
                            self.sheet_config.industry_column,
                            self.sheet_config.website_column,
                            self.sheet_config.phone_column,
                            self.sheet_config.location_column,
                            self.sheet_config.notes_column,
                        ] and value:
                            custom_fields[key] = value
                    
                    lead_data['custom_fields'] = custom_fields
                    
                    # Skip if required fields are missing
                    if not all([lead_data.get('email'), lead_data.get('first_name'), 
                               lead_data.get('last_name'), lead_data.get('company')]):
                        logger.warning(f"Skipping incomplete lead record: {record}")
                        continue
                    
                    lead = Lead(**lead_data)
                    leads.append(lead)
                    
                except Exception as e:
                    logger.error(f"Error processing lead record {record}: {e}")
                    continue
            
            logger.info(f"Successfully read {len(leads)} leads from sheet")
            return leads
            
        except Exception as e:
            logger.error(f"Failed to read leads from sheet: {e}")
            raise
    
    def write_results(self, emails: List[GeneratedEmail], sheet_name: Optional[str] = None):
        """Write email generation results to Google Sheets.
        
        Args:
            emails: List of generated emails
            sheet_name: Name of the results sheet
        """
        if not self.client:
            raise ValueError("Google Sheets client not authenticated")
        
        sheet_name = sheet_name or self.sheet_config.results_sheet
        
        try:
            logger.info(f"Writing {len(emails)} results to sheet: {sheet_name}")
            
            worksheet = self._get_worksheet(sheet_name)
            
            # Clear existing content
            worksheet.clear()
            
            # Prepare headers
            headers = [
                self.sheet_config.email_column,
                self.sheet_config.first_name_column,
                self.sheet_config.last_name_column,
                self.sheet_config.company_column,
                self.sheet_config.status_column,
                self.sheet_config.generated_at_column,
                self.sheet_config.sent_at_column,
                self.sheet_config.subject_column,
                self.sheet_config.body_column,
                self.sheet_config.error_column,
                self.sheet_config.ab_variant_column,
            ]
            
            # Prepare data rows
            rows = [headers]
            for email in emails:
                row = [
                    email.lead.email,
                    email.lead.first_name,
                    email.lead.last_name,
                    email.lead.company,
                    email.status.value,
                    email.generated_at.isoformat() if email.generated_at else '',
                    email.sent_at.isoformat() if email.sent_at else '',
                    email.subject,
                    email.body[:1000] + '...' if len(email.body) > 1000 else email.body,  # Truncate long bodies
                    email.error_message or '',
                    email.ab_variant.value if email.ab_variant else '',
                ]
                rows.append(row)
            
            # Write to sheet
            worksheet.update(rows)
            
            logger.info(f"Successfully wrote results to sheet")
            
        except Exception as e:
            logger.error(f"Failed to write results to sheet: {e}")
            raise
    
    def update_lead_status(self, email: str, status: str, sheet_name: Optional[str] = None):
        """Update the status of a specific lead.
        
        Args:
            email: Lead email address
            status: New status
            sheet_name: Name of the leads sheet
        """
        if not self.client:
            raise ValueError("Google Sheets client not authenticated")
        
        sheet_name = sheet_name or self.sheet_config.leads_sheet
        
        try:
            worksheet = self._get_worksheet(sheet_name)
            
            # Find the lead row
            email_col = worksheet.find(email)
            if email_col:
                # Find status column or add it
                try:
                    status_col = worksheet.find(self.sheet_config.status_column)
                    if not status_col:
                        # Add status column header
                        headers = worksheet.row_values(1)
                        status_col_index = len(headers) + 1
                        worksheet.update_cell(1, status_col_index, self.sheet_config.status_column)
                    else:
                        status_col_index = status_col.col
                    
                    # Update status
                    worksheet.update_cell(email_col.row, status_col_index, status)
                    logger.info(f"Updated status for {email} to {status}")
                    
                except Exception as e:
                    logger.error(f"Failed to update status for {email}: {e}")
            
        except Exception as e:
            logger.error(f"Failed to find lead {email}: {e}")
    
    def get_sheet_info(self) -> Dict[str, Any]:
        """Get information about the spreadsheet.
        
        Returns:
            Dictionary with spreadsheet information
        """
        if not self.spreadsheet:
            return {}
        
        try:
            worksheets = [ws.title for ws in self.spreadsheet.worksheets()]
            return {
                'title': self.spreadsheet.title,
                'id': self.spreadsheet.id,
                'worksheets': worksheets,
                'url': self.spreadsheet.url,
            }
        except Exception as e:
            logger.error(f"Failed to get sheet info: {e}")
            return {}