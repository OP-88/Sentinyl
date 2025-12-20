"""
Configuration management for Sentinyl API
Uses Pydantic Settings for environment variable validation
"""
from pydantic_settings import BaseSettings
from typing import Optional, List


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
    
    # Stripe Integration
    STRIPE_API_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    
    # Application Settings
    APP_NAME: str = "Sentinyl"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # CORS Settings - Comma-separated list of allowed origins
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    
    # Worker Settings
    WORKER_POLL_INTERVAL: int = 5  # seconds
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse comma-separated origins into a list"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(',') if origin.strip()]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()

