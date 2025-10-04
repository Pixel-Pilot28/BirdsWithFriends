"""
Configuration management for the ingest service.
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Cornell Lab stream configuration
    cornell_cam_url: str = "https://www.youtube.com/watch?v=x10vL6_47Dw"
    
    # Sampling configuration
    sample_interval: int = 10  # seconds between captures
    audio_duration: int = 5    # duration of audio clips in seconds
    
    # Output configuration
    output_dir: str = "./output"
    s3_bucket: Optional[str] = None
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    
    # Service configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    """Get application settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()

# Ensure output directory exists
os.makedirs(settings.output_dir, exist_ok=True)