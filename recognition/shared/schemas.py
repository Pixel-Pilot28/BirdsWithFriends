"""
Shared schemas and utilities for recognition services.
"""

from datetime import datetime
from typing import List, Optional, Literal, Union
from pydantic import BaseModel, Field
import re


class BoundingBox(BaseModel):
    """Bounding box coordinates for image detections."""
    x: float = Field(..., description="X coordinate (0-1 normalized)")
    y: float = Field(..., description="Y coordinate (0-1 normalized)")
    width: float = Field(..., description="Width (0-1 normalized)")
    height: float = Field(..., description="Height (0-1 normalized)")


class Detection(BaseModel):
    """Individual species detection."""
    species: str = Field(..., description="Species name (e.g., 'Northern Cardinal')")
    count: int = Field(1, ge=1, description="Number of individuals detected")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    bbox: Optional[BoundingBox] = Field(None, description="Bounding box for image detections")
    low_confidence: bool = Field(False, description="True if below minimum confidence threshold")


class Character(BaseModel):
    """Individual character instance for storytelling."""
    id: str = Field(..., description="Unique character identifier")
    species: str = Field(..., description="Species name")


class RecognitionEvent(BaseModel):
    """Unified recognition event schema."""
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    source: Literal["audio", "image"] = Field(..., description="Recognition source type")
    detections: List[Detection] = Field(..., description="List of species detections")
    characters: List[Character] = Field(default_factory=list, description="Character instances for storytelling")
    snapshot_url: Optional[str] = Field(None, description="URL to the analyzed media")


class RecognitionRequest(BaseModel):
    """Request payload for recognition services."""
    url: Optional[str] = Field(None, description="URL to media file")
    # Note: For binary data, we'll handle as form data or multipart upload


def generate_character_id(species: str, index: int = 1) -> str:
    """
    Generate a unique character ID from species name.
    
    Args:
        species: Species name (e.g., "Northern Cardinal")
        index: Instance number for multiple individuals
        
    Returns:
        Unique character ID (e.g., "northern_cardinal_1")
    """
    # Convert to lowercase, replace spaces with underscores, remove special chars
    clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', species.lower())
    clean_name = re.sub(r'\s+', '_', clean_name.strip())
    return f"{clean_name}_{index}"


def create_characters_from_detection(detection: Detection) -> List[Character]:
    """
    Create character instances from a detection based on count.
    
    Args:
        detection: Detection with species and count
        
    Returns:
        List of Character instances
    """
    characters = []
    
    if detection.count > 1:
        for i in range(1, detection.count + 1):
            char_id = generate_character_id(detection.species, i)
            characters.append(Character(
                id=char_id,
                species=detection.species
            ))
    
    return characters


def apply_confidence_threshold(detection: Detection, min_confidence: float) -> Detection:
    """
    Apply confidence threshold to detection and set low_confidence flag.
    
    Args:
        detection: Detection to evaluate
        min_confidence: Minimum confidence threshold
        
    Returns:
        Detection with low_confidence flag set
    """
    detection.low_confidence = detection.confidence < min_confidence
    return detection