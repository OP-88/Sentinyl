"""
Configuration management for Sentinyl API
Uses Pydantic Settings for environment variable validation
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database
    DATABASE_URL: str = "postgresql://sentinyl:sentinyl_secure_pass@localhost:5432/sentinyldb"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Slack Notifications
    SLACK_WEBHOOK_URL: Optional[str] = None
    
    # GitHub API
    GITHUB_TOKEN: Optional[str] = None
    
    # Application Settings
    APP_NAME: str = "Sentinyl"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # Worker Settings
    WORKER_POLL_INTERVAL: int = 5  # seconds
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
