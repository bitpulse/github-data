import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseSettings, Field

# Load environment variables
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # GitHub API
    github_token: str = Field(..., env='GITHUB_TOKEN')
    github_api_base_url: str = Field(default='https://api.github.com', env='GITHUB_API_BASE_URL')
    
    # MongoDB
    mongodb_uri: str = Field(default='mongodb://localhost:27017/', env='MONGODB_URI')
    mongodb_database: str = Field(default='github_crypto_analysis', env='MONGODB_DATABASE')
    
    # Time Series Collections
    repo_stats_collection: str = Field(default='repo_stats_timeseries')
    contributor_activity_collection: str = Field(default='contributor_activity_timeseries')
    release_milestones_collection: str = Field(default='release_milestones_timeseries')
    
    # Collection Configuration
    collection_interval_hours: int = Field(default=1, env='COLLECTION_INTERVAL_HOURS')
    batch_size: int = Field(default=100, env='BATCH_SIZE')
    
    # Rate Limiting
    rate_limit_requests_per_hour: int = Field(default=5000, env='RATE_LIMIT_REQUESTS_PER_HOUR')
    rate_limit_buffer: float = Field(default=0.8, env='RATE_LIMIT_BUFFER')
    
    # Time Series Configuration
    timeseries_granularity: str = Field(default='hours')
    data_retention_days: int = Field(default=365, env='DATA_RETENTION_DAYS')
    
    # Logging
    log_level: str = Field(default='INFO', env='LOG_LEVEL')
    log_file: Optional[str] = Field(default='logs/github_collector.log', env='LOG_FILE')
    
    class Config:
        env_file = '.env'
        case_sensitive = False


# Create global settings instance
settings = Settings()


# Validate settings on import
def validate_settings():
    """Validate critical settings"""
    if not settings.github_token or settings.github_token == 'your_github_personal_access_token_here':
        raise ValueError("Please set GITHUB_TOKEN in your .env file")
    
    if not settings.mongodb_uri:
        raise ValueError("Please set MONGODB_URI in your .env file")
    
    return True