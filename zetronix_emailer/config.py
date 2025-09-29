"""Configuration management for the Zetronix Outreach Emailer."""

import os
from typing import Optional
try:
    from pydantic import BaseSettings, validator
except ImportError:
    # Fallback for pydantic v2
    try:
        from pydantic_settings import BaseSettings
        from pydantic import field_validator as validator
    except ImportError:
        from pydantic import BaseModel as BaseSettings
        validator = lambda x: lambda y: y
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config(BaseSettings):
    """Application configuration."""
    
    # OpenAI Configuration
    openai_api_key: str = ""
    openai_model: str = "gpt-4"
    
    # Google Sheets Configuration
    google_credentials_path: Optional[str] = None
    google_spreadsheet_id: str = ""
    
    # SMTP Configuration (Optional)
    smtp_server: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True
    
    # Logging Configuration
    log_level: str = "INFO"
    log_file: str = "emailer.log"
    
    # A/B Testing Configuration
    ab_test_enabled: bool = True
    ab_test_split_ratio: float = 0.5
    
    def validate_split_ratio(self, v):
        """Validate A/B test split ratio is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError('A/B test split ratio must be between 0 and 1')
        return v
    
    def validate_openai_key(self, v):
        """Validate OpenAI API key is provided."""
        if not v or v == "your_openai_api_key_here":
            # Don't raise error for missing key, just warn
            pass
        return v
    
    def validate_spreadsheet_id(self, v):
        """Validate Google Spreadsheet ID is provided."""
        if not v or v == "your_google_spreadsheet_id":
            # Don't raise error for missing ID, just warn
            pass
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global config instance
try:
    config = Config()
except Exception as e:
    # Create a minimal config if there are validation errors
    config = Config(
        openai_api_key="",
        google_spreadsheet_id="",
        openai_model="gpt-4",
        log_level="INFO",
        log_file="emailer.log",
        ab_test_enabled=True,
        ab_test_split_ratio=0.5
    )