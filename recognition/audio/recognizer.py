"""
BirdCAGE Audio Recognition Service

HTTP adapter for BirdCAGE audio recognition model.
"""
import logging
import random
from typing import List, BinaryIO
from pathlib import Path

from ..shared.base import BaseRecognizer
from ..shared.schemas import Detection
from ..shared.config import AudioRecognitionSettings

logger = logging.getLogger(__name__)


class MockBirdCAGERecognizer:
    """
    Mock BirdCAGE recognizer for development/testing.
    
    In production, this would integrate with the actual BirdCAGE model.
    """
    
    # Mock species database with realistic confidence ranges
    SPECIES_DATABASE = [
        ("Northern Cardinal", 0.85, 0.95),
        ("Blue Jay", 0.70, 0.90),
        ("American Robin", 0.75, 0.92),
        ("House Sparrow", 0.65, 0.88),
        ("Red-winged Blackbird", 0.80, 0.94),
        ("Common Grackle", 0.72, 0.87),
        ("European Starling", 0.68, 0.85),
        ("Mourning Dove", 0.78, 0.91),
        ("Rock Pigeon", 0.74, 0.89),
        ("American Crow", 0.82, 0.96),
    ]
    
    def __init__(self, model_path: str = None, config_path: str = None):
        self.model_path = model_path
        self.config_path = config_path
        logger.info("Mock BirdCAGE recognizer initialized")
    
    def recognize(self, audio_path: Path) -> List[Detection]:
        """
        Mock audio recognition.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            List of mock detections
        """
        logger.info(f"Processing audio file: {audio_path}")
        
        # Simulate processing time and variable results
        detections = []
        
        # Randomly detect 0-3 species
        num_detections = random.randint(0, 3)
        
        if num_detections > 0:
            # Select random species
            selected_species = random.sample(self.SPECIES_DATABASE, num_detections)
            
            for species_name, min_conf, max_conf in selected_species:
                confidence = random.uniform(min_conf, max_conf)
                
                # Occasionally detect multiple individuals
                count = 1
                if random.random() < 0.3:  # 30% chance of multiple
                    count = random.randint(2, 4)
                
                detection = Detection(
                    species=species_name,
                    count=count,
                    confidence=confidence
                )
                detections.append(detection)
                
                logger.info(f"Detected: {species_name} (count={count}, confidence={confidence:.3f})")
        
        return detections


class AudioRecognizer(BaseRecognizer):
    """BirdCAGE audio recognition adapter."""
    
    def __init__(self, settings: AudioRecognitionSettings):
        super().__init__(settings)
        
        # Initialize BirdCAGE model (mock for now)
        self.model = MockBirdCAGERecognizer(
            model_path=settings.birdcage_model_path,
            config_path=settings.birdcage_config_path
        )
        
        logger.info("AudioRecognizer initialized")
    
    async def recognize_from_url(self, url: str) -> List[Detection]:
        """
        Recognize species from audio URL.
        
        Args:
            url: URL to audio file
            
        Returns:
            List of detections
        """
        # TODO: Download audio file from URL
        # For now, simulate processing
        logger.warning(f"URL recognition not fully implemented: {url}")
        
        # Mock detection based on URL
        return self.model.recognize(Path("mock_audio.wav"))
    
    async def recognize_from_file(self, file_data: BinaryIO, filename: str) -> List[Detection]:
        """
        Recognize species from uploaded audio file.
        
        Args:
            file_data: Binary audio data
            filename: Original filename
            
        Returns:
            List of detections
        """
        temp_path = None
        try:
            # Save to temporary file
            temp_path = self.save_temp_file(file_data, filename)
            
            # Validate audio format
            if not self._is_valid_audio_file(temp_path):
                raise ValueError(f"Unsupported audio format: {filename}")
            
            # Run recognition
            detections = self.model.recognize(temp_path)
            
            return detections
            
        finally:
            if temp_path:
                self.cleanup_temp_file(temp_path)
    
    def _is_valid_audio_file(self, file_path: Path) -> bool:
        """Check if file is a valid audio format."""
        suffix = file_path.suffix.lower().lstrip('.')
        return suffix in self.settings.allowed_audio_types