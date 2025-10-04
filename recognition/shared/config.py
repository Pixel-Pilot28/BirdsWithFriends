"""
Base configuration for recognition services.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class RecognitionSettings(BaseSettings):
    """Base settings for recognition services."""
    
    # Confidence thresholds
    min_confidence: float = 0.6
    
    # Service configuration
    host: str = "0.0.0.0"
    debug: bool = True
    
    # File handling
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    allowed_audio_types: list = ["wav", "mp3", "m4a", "flac"]
    allowed_image_types: list = ["jpg", "jpeg", "png", "bmp"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra environment variables


class AudioRecognitionSettings(RecognitionSettings):
    """Settings for audio recognition service."""
    
    port: int = 8002
    service_name: str = "audio-recognizer"
    
    # BirdCAGE specific settings
    birdcage_model_path: Optional[str] = None
    birdcage_config_path: Optional[str] = None


class ImageRecognitionSettings(RecognitionSettings):
    """Settings for image recognition service."""
    
    port: int = 8003
    service_name: str = "image-recognizer"
    
    # WhosAtMyFeeder specific settings
    whosat_model_path: Optional[str] = None
    whosat_config_path: Optional[str] = None