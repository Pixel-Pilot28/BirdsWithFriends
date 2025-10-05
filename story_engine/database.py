"""
Database models for Story Engine.

SQLAlchemy models for storing stories, episodes, and generation metadata.
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .models import EpisodeStatus

Base = declarative_base()


class Story(Base):
    """Main story record with metadata."""
    
    __tablename__ = "stories"
    
    id = Column(String, primary_key=True)  # UUID format
    user_id = Column(String, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Story configuration
    story_type = Column(String(50), nullable=False)  # e.g., "Real Housewives"
    age_group = Column(String(20), nullable=False)   # e.g., "child", "adult", "age:5"
    content_rating = Column(String(10), default="G") # G, PG, PG-13
    target_length = Column(String(20), nullable=False) # short, medium, long
    
    # Episode planning
    total_episodes = Column(Integer, default=1, nullable=False)
    completed_episodes = Column(Integer, default=0, nullable=False)
    
    # Serialized scheduling
    start_date = Column(DateTime, nullable=True)  # When to start releasing episodes
    release_frequency = Column(String(20), default="daily")  # daily, weekly, custom
    timezone = Column(String(50), default="UTC")  # User's timezone
    next_release_at = Column(DateTime, nullable=True)  # Next scheduled episode release
    is_serialized = Column(Boolean, default=False)  # True if episodes release over time
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Story context (JSON storage)
    characters_data = Column(JSON, nullable=True)    # Character information used
    species_data = Column(JSON, nullable=True)       # Species counts used
    user_preferences = Column(JSON, nullable=True)   # User preferences used
    time_range = Column(JSON, nullable=True)         # Time range data came from
    
    # Generation metadata
    template_used = Column(String(100), nullable=True)
    llm_provider = Column(String(50), default="mock")
    total_tokens_used = Column(Integer, default=0)
    average_safety_score = Column(Float, default=1.0)
    
    # Status
    status = Column(String(20), default="active")  # active, completed, archived
    
    # Relationships
    episodes = relationship("Episode", back_populates="story", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Story(id='{self.id}', title='{self.title}', episodes={self.completed_episodes}/{self.total_episodes})>"


class Episode(Base):
    """Individual story episode."""
    
    __tablename__ = "episodes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    story_id = Column(String, ForeignKey("stories.id"), nullable=False, index=True)
    episode_index = Column(Integer, nullable=False)  # 1, 2, 3, etc.
    
    # Content
    title = Column(String(255), nullable=True)
    text = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    
    # Metadata
    word_count = Column(Integer, default=0)
    tokens_used = Column(Integer, default=0)
    generation_time = Column(Float, default=0.0)
    safety_score = Column(Float, default=1.0)
    content_warnings = Column(JSON, nullable=True)  # List of warnings
    
    # Publication
    status = Column(String(20), default="draft")  # draft, scheduled, published, archived
    published_at = Column(DateTime, nullable=True)
    scheduled_for = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Generation details
    template_used = Column(String(100), nullable=True)
    llm_model = Column(String(50), nullable=True)
    generation_parameters = Column(JSON, nullable=True)  # temperature, max_tokens, etc.
    
    # Relationships
    story = relationship("Story", back_populates="episodes")
    
    def __repr__(self):
        return f"<Episode(id={self.id}, story='{self.story_id}', index={self.episode_index}, status='{self.status}')>"


class GenerationLog(Base):
    """Log of story generation attempts and results."""
    
    __tablename__ = "generation_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    story_id = Column(String, ForeignKey("stories.id"), nullable=False, index=True)
    episode_id = Column(Integer, ForeignKey("episodes.id"), nullable=True, index=True)
    
    # Request details
    user_id = Column(String, nullable=False)
    request_data = Column(JSON, nullable=False)  # Full StoryRequest
    template_name = Column(String(100), nullable=True)
    
    # Generation details
    llm_provider = Column(String(50), nullable=False)
    llm_model = Column(String(50), nullable=True)
    system_prompt = Column(Text, nullable=True)
    user_prompt = Column(Text, nullable=True)
    generation_parameters = Column(JSON, nullable=True)
    
    # Results
    success = Column(Boolean, default=False)
    generated_text = Column(Text, nullable=True)
    tokens_used = Column(Integer, default=0)
    generation_time = Column(Float, default=0.0)
    
    # Quality metrics
    safety_score = Column(Float, nullable=True)
    content_warnings = Column(JSON, nullable=True)
    word_count = Column(Integer, default=0)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Timestamp
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    def __repr__(self):
        status = "✓" if self.success else "✗"
        return f"<GenerationLog(id={self.id}, story='{self.story_id}', {status}, tokens={self.tokens_used})>"


class ContentModeration(Base):
    """Content moderation results and actions."""
    
    __tablename__ = "content_moderation"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    episode_id = Column(Integer, ForeignKey("episodes.id"), nullable=False, index=True)
    
    # Moderation details
    moderation_service = Column(String(50), nullable=False)  # "internal", "openai", etc.
    moderation_version = Column(String(20), nullable=True)
    
    # Results
    is_safe = Column(Boolean, default=True)
    safety_score = Column(Float, default=1.0)
    flagged_categories = Column(JSON, nullable=True)  # List of flagged content types
    
    # Actions taken
    action_taken = Column(String(50), nullable=True)  # "none", "filtered", "blocked", "regenerated"
    original_text = Column(Text, nullable=True)       # Original text if modified
    modified_text = Column(Text, nullable=True)       # Modified text if filtered
    
    # Human review
    requires_human_review = Column(Boolean, default=False)
    human_reviewed = Column(Boolean, default=False)
    human_reviewer = Column(String(100), nullable=True)
    human_decision = Column(String(50), nullable=True)  # "approved", "rejected", "modified"
    review_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        status = "SAFE" if self.is_safe else "FLAGGED"
        return f"<ContentModeration(id={self.id}, episode={self.episode_id}, {status}, score={self.safety_score})>"


# Database configuration
DATABASE_URL = "sqlite:///./story_data/stories.db"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Database dependency
def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()