"""Configuration management using Pydantic Settings"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database Configuration
    database_url: str = Field(
        default="sqlite:///./data/meetmind.db",
        description="Database connection URL"
    )
    
    # Upload Configuration
    upload_dir: str = Field(
        default="./uploads",
        description="Directory for temporary audio file storage"
    )
    max_upload_size_mb: int = Field(
        default=100,
        description="Maximum upload file size in MB"
    )
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key for LangGraph LLM"
    )
    
    # Application Configuration
    app_name: str = Field(
        default="MeetMind",
        description="Application name"
    )
    debug: bool = Field(
        default=True,
        description="Debug mode"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()

# Ensure required directories exist
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(os.path.dirname(settings.database_url.replace("sqlite:///", "")), exist_ok=True)
