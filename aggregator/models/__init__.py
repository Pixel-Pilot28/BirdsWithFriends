"""
Database models for character management and event storage.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pydantic import BaseModel
from enum import Enum

from ..database import Base


class Character(Base):
    """Character model for storing bird character instances."""
    
    __tablename__ = "characters"
    
    id = Column(String, primary_key=True)  # e.g., "northern_cardinal_1"
    species = Column(String, nullable=False)  # e.g., "Northern Cardinal"
    archetype = Column(String, nullable=True)  # e.g., "bold gossip"
    first_seen = Column(DateTime, default=func.now(), nullable=False)
    last_seen = Column(DateTime, default=func.now(), nullable=False)
    appearance_count = Column(Integer, default=1, nullable=False)
    notes = Column(Text, nullable=True)  # User-editable notes
    
    # Relationships
    events = relationship("RecognitionEventDB", back_populates="character", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Character(id='{self.id}', species='{self.species}', archetype='{self.archetype}')>"


class RecognitionEventDB(Base):
    """Database model for storing recognition events."""
    
    __tablename__ = "recognition_events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False)
    source = Column(String, nullable=False)  # "audio" or "image"
    species = Column(String, nullable=False)
    count = Column(Integer, nullable=False)
    confidence = Column(Float, nullable=False)
    low_confidence = Column(Boolean, default=False)
    bbox = Column(JSON, nullable=True)  # Bounding box for images
    snapshot_url = Column(String, nullable=True)
    character_id = Column(String, ForeignKey("characters.id"), nullable=True)
    
    # Relationships
    character = relationship("Character", back_populates="events")
    
    def __repr__(self):
        return f"<RecognitionEvent(species='{self.species}', count={self.count}, timestamp='{self.timestamp}')>"


class AggregationSummary(Base):
    """Database model for storing aggregated summaries."""
    
    __tablename__ = "aggregation_summaries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    species_counts = Column(JSON, nullable=False)  # {"Northern Cardinal": 3, "Blue Jay": 1}
    active_characters = Column(JSON, nullable=False)  # [{"id": "cardinal_1", "species": "Northern Cardinal"}]
    dominant_snapshot = Column(String, nullable=True)  # URL to most confident detection
    total_detections = Column(Integer, default=0)
    average_confidence = Column(Float, default=0.0)
    
    def __repr__(self):
        return f"<AggregationSummary(start='{self.start_time}', species={len(self.species_counts)})>"


# Pydantic models for API responses
class CharacterResponse(BaseModel):
    """Pydantic model for character API responses."""
    
    id: str
    species: str
    archetype: Optional[str] = None
    first_seen: datetime
    last_seen: datetime
    appearance_count: int
    notes: Optional[str] = None
    
    class Config:
        from_attributes = True


class CharacterUpdate(BaseModel):
    """Pydantic model for character updates."""
    
    archetype: Optional[str] = None
    notes: Optional[str] = None


class RecognitionEventResponse(BaseModel):
    """Pydantic model for recognition event responses."""
    
    id: int
    timestamp: datetime
    source: str
    species: str
    count: int
    confidence: float
    low_confidence: bool
    bbox: Optional[dict] = None
    snapshot_url: Optional[str] = None
    character_id: Optional[str] = None
    
    class Config:
        from_attributes = True


class AggregationSummaryResponse(BaseModel):
    """Pydantic model for aggregation summary responses."""
    
    id: int
    start_time: datetime
    end_time: datetime
    species_counts: dict
    active_characters: List[dict]
    dominant_snapshot: Optional[str] = None
    total_detections: int
    average_confidence: float
    
    class Config:
        from_attributes = True


class StoryInput(BaseModel):
    """Pydantic model for story generation input."""
    
    timeframe: dict  # {"start": "2025-10-04T12:00:00Z", "end": "2025-10-04T12:01:00Z"}
    characters: List[CharacterResponse]
    species_activity: dict  # {"Northern Cardinal": {"count": 3, "confidence": 0.89}}
    dominant_snapshot: Optional[str] = None
    context: dict  # Additional context for story generation