"""
WhosAtMyFeeder Image Recognition Service

HTTP adapter for WhosAtMyFeeder image recognition model.
"""
import logging
import random
from typing import List, BinaryIO
from pathlib import Path

from ..shared.base import BaseRecognizer
from ..shared.schemas import Detection, BoundingBox
from ..shared.config import ImageRecognitionSettings

logger = logging.getLogger(__name__)


class MockWhosAtMyFeederRecognizer:
    """
    Mock WhosAtMyFeeder recognizer for development/testing.
    
    In production, this would integrate with the actual WhosAtMyFeeder model.
    """
    
    # Mock species database with realistic confidence ranges and bounding boxes
    SPECIES_DATABASE = [
        ("Northern Cardinal", 0.80, 0.96),
        ("Blue Jay", 0.75, 0.92),
        ("American Robin", 0.78, 0.94),
        ("House Sparrow", 0.70, 0.88),
        ("Red-winged Blackbird", 0.82, 0.95),
        ("Common Grackle", 0.74, 0.89),
        ("European Starling", 0.71, 0.87),
        ("Mourning Dove", 0.76, 0.93),
        ("Rock Pigeon", 0.73, 0.90),
        ("American Goldfinch", 0.79, 0.94),
        ("House Finch", 0.77, 0.91),
        ("Downy Woodpecker", 0.81, 0.95),
    ]
    
    def __init__(self, model_path: str = None, config_path: str = None):
        self.model_path = model_path
        self.config_path = config_path
        logger.info("Mock WhosAtMyFeeder recognizer initialized")
    
    def recognize(self, image_path: Path) -> List[Detection]:
        """
        Mock image recognition.
        
        Args:
            image_path: Path to image file
            
        Returns:
            List of mock detections with bounding boxes
        """
        logger.info(f"Processing image file: {image_path}")
        
        # Simulate processing time and variable results
        detections = []
        
        # Randomly detect 0-4 species (images can show multiple birds)
        num_detections = random.randint(0, 4)
        
        if num_detections > 0:
            # Select random species
            selected_species = random.sample(
                self.SPECIES_DATABASE, 
                min(num_detections, len(self.SPECIES_DATABASE))
            )
            
            for species_name, min_conf, max_conf in selected_species:
                confidence = random.uniform(min_conf, max_conf)
                
                # Generate random bounding box
                x = random.uniform(0.1, 0.6)
                y = random.uniform(0.1, 0.6)
                width = random.uniform(0.15, 0.4)
                height = random.uniform(0.15, 0.4)
                
                bbox = BoundingBox(x=x, y=y, width=width, height=height)
                
                # Image recognition typically detects single individuals per bbox
                # But occasionally might detect flocks
                count = 1
                if random.random() < 0.2:  # 20% chance of multiple in same area
                    count = random.randint(2, 3)
                
                detection = Detection(
                    species=species_name,
                    count=count,
                    confidence=confidence,
                    bbox=bbox
                )
                detections.append(detection)
                
                logger.info(f"Detected: {species_name} (count={count}, confidence={confidence:.3f}, bbox={bbox})")
        
        return detections


class ImageRecognizer(BaseRecognizer):
    """WhosAtMyFeeder image recognition adapter."""
    
    def __init__(self, settings: ImageRecognitionSettings):
        super().__init__(settings)
        
        # Initialize WhosAtMyFeeder model (mock for now)
        self.model = MockWhosAtMyFeederRecognizer(
            model_path=settings.whosat_model_path,
            config_path=settings.whosat_config_path
        )
        
        logger.info("ImageRecognizer initialized")
    
    async def recognize_from_url(self, url: str) -> List[Detection]:
        """
        Recognize species from image URL.
        
        Args:
            url: URL to image file
            
        Returns:
            List of detections
        """
        # TODO: Download image file from URL
        # For now, simulate processing
        logger.warning(f"URL recognition not fully implemented: {url}")
        
        # Mock detection based on URL
        return self.model.recognize(Path("mock_image.jpg"))
    
    async def recognize_from_file(self, file_data: BinaryIO, filename: str) -> List[Detection]:
        """
        Recognize species from uploaded image file.
        
        Args:
            file_data: Binary image data
            filename: Original filename
            
        Returns:
            List of detections
        """
        temp_path = None
        try:
            # Save to temporary file
            temp_path = self.save_temp_file(file_data, filename)
            
            # Validate image format
            if not self._is_valid_image_file(temp_path):
                raise ValueError(f"Unsupported image format: {filename}")
            
            # Run recognition
            detections = self.model.recognize(temp_path)
            
            return detections
            
        finally:
            if temp_path:
                self.cleanup_temp_file(temp_path)
    
    def _is_valid_image_file(self, file_path: Path) -> bool:
        """Check if file is a valid image format."""
        suffix = file_path.suffix.lower().lstrip('.')
        return suffix in self.settings.allowed_image_types