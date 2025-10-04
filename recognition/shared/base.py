"""
Base classes for recognition adapters.
"""
import tempfile
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Union, BinaryIO
from pathlib import Path

from .schemas import RecognitionEvent, Detection
from .config import RecognitionSettings


class BaseRecognizer(ABC):
    """Abstract base class for recognition adapters."""
    
    def __init__(self, settings: RecognitionSettings):
        self.settings = settings
        self.min_confidence = settings.min_confidence
    
    @abstractmethod
    async def recognize_from_url(self, url: str) -> List[Detection]:
        """
        Recognize species from a media URL.
        
        Args:
            url: URL to the media file
            
        Returns:
            List of detections
        """
        pass
    
    @abstractmethod
    async def recognize_from_file(self, file_data: BinaryIO, filename: str) -> List[Detection]:
        """
        Recognize species from uploaded file data.
        
        Args:
            file_data: Binary file data
            filename: Original filename
            
        Returns:
            List of detections
        """
        pass
    
    def create_event(
        self, 
        detections: List[Detection], 
        source: str, 
        snapshot_url: str = None
    ) -> RecognitionEvent:
        """
        Create a unified recognition event from detections.
        
        Args:
            detections: List of species detections
            source: "audio" or "image"
            snapshot_url: URL to the analyzed media
            
        Returns:
            RecognitionEvent with characters generated
        """
        from .schemas import create_characters_from_detection, apply_confidence_threshold
        
        # Apply confidence thresholds
        processed_detections = [
            apply_confidence_threshold(detection, self.min_confidence)
            for detection in detections
        ]
        
        # Generate characters for multi-count detections
        all_characters = []
        for detection in processed_detections:
            characters = create_characters_from_detection(detection)
            all_characters.extend(characters)
        
        return RecognitionEvent(
            timestamp=datetime.utcnow().isoformat() + "Z",
            source=source,
            detections=processed_detections,
            characters=all_characters,
            snapshot_url=snapshot_url
        )
    
    def save_temp_file(self, file_data: BinaryIO, filename: str) -> Path:
        """
        Save uploaded file to temporary location.
        
        Args:
            file_data: Binary file data
            filename: Original filename for extension detection
            
        Returns:
            Path to temporary file
        """
        suffix = Path(filename).suffix
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        
        try:
            file_data.seek(0)
            temp_file.write(file_data.read())
            temp_file.flush()
            return Path(temp_file.name)
        finally:
            temp_file.close()
    
    def cleanup_temp_file(self, file_path: Path):
        """Clean up temporary file."""
        try:
            if file_path.exists():
                os.unlink(file_path)
        except Exception:
            pass  # Ignore cleanup errors