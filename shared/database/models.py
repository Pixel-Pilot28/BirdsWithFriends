"""
Unified database models for Birds with Friends.

Contains all database table definitions according to Feature 9 specification:
- users(id, email, phone, timezone, preferences_json, created_at)
- snapshots(id, url, timestamp, source_event_id)
- recognition_events(id, payload_json, created_at)
- characters(id, species, archetype, first_seen, last_seen, placeholder_bool)
- stories(id, user_id, title, total_episodes, start_date, release_frequency, status, created_at)
- episodes(id, story_id, index, text, published_at, status)
- notifications(id, user_id, channel, subscription_json, last_sent_at)
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .config import Base


# Core User Management

class User(Base):
    """User table - core user information and preferences."""
    
    __tablename__ = "users"
    
    # Primary fields as specified
    id = Column(String, primary_key=True)  # UUID or username
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(20), nullable=True)
    timezone = Column(String(50), default="UTC", nullable=False)
    preferences_json = Column(JSON, nullable=True)  # User preferences as JSON
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    stories = relationship("Story", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id='{self.id}', email='{self.email}')>"


# Recognition and Data Capture

class RecognitionEvent(Base):
    """Recognition events table - stores all AI recognition results."""
    
    __tablename__ = "recognition_events"
    
    # Primary fields as specified
    id = Column(Integer, primary_key=True, autoincrement=True)
    payload_json = Column(JSON, nullable=False)  # Complete recognition data
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    snapshots = relationship("Snapshot", back_populates="source_event", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<RecognitionEvent(id={self.id}, created_at='{self.created_at}')>"


class Snapshot(Base):
    """Snapshots table - captured images/audio with metadata."""
    
    __tablename__ = "snapshots"
    
    # Primary fields as specified
    id = Column(String, primary_key=True)  # UUID or filename-based ID
    url = Column(String(500), nullable=False)  # File path or S3 URL
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    source_event_id = Column(Integer, ForeignKey("recognition_events.id"), nullable=True)
    
    # Relationships
    source_event = relationship("RecognitionEvent", back_populates="snapshots")
    
    def __repr__(self):
        return f"<Snapshot(id='{self.id}', url='{self.url}')>"


# Character Management

class Character(Base):
    """Characters table - bird character instances with personality."""
    
    __tablename__ = "characters"
    
    # Primary fields as specified
    id = Column(String, primary_key=True)  # e.g., "northern_cardinal_1"
    species = Column(String, nullable=False)
    archetype = Column(String, nullable=True)  # Personality archetype
    first_seen = Column(DateTime, default=func.now(), nullable=False)
    last_seen = Column(DateTime, default=func.now(), nullable=False)
    placeholder_bool = Column(Boolean, default=False, nullable=False)  # Is this a placeholder?
    
    def __repr__(self):
        return f"<Character(id='{self.id}', species='{self.species}', archetype='{self.archetype}')>"


# Story Engine

class Story(Base):
    """Stories table - main story records with metadata."""
    
    __tablename__ = "stories"
    
    # Primary fields as specified
    id = Column(String, primary_key=True)  # UUID format
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    total_episodes = Column(Integer, default=1, nullable=False)
    start_date = Column(DateTime, nullable=True)  # When story starts
    release_frequency = Column(String(20), default="daily")  # daily, weekly, custom
    status = Column(String(20), default="draft")  # draft, scheduled, published, completed
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="stories")
    episodes = relationship("Episode", back_populates="story", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="story", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Story(id='{self.id}', title='{self.title}', user_id='{self.user_id}')>"


class Episode(Base):
    """Episodes table - individual story episodes."""
    
    __tablename__ = "episodes"
    
    # Primary fields as specified
    id = Column(String, primary_key=True)  # UUID format
    story_id = Column(String, ForeignKey("stories.id"), nullable=False, index=True)
    index = Column(Integer, nullable=False)  # Episode number (1, 2, 3...)
    text = Column(Text, nullable=False)  # Episode content
    published_at = Column(DateTime, nullable=True)  # When episode was published
    status = Column(String(20), default="draft")  # draft, scheduled, published
    
    # Relationships
    story = relationship("Story", back_populates="episodes")
    
    def __repr__(self):
        return f"<Episode(id='{self.id}', story_id='{self.story_id}', index={self.index})>"


# Notification System

class Notification(Base):
    """Notifications table - notification delivery tracking."""
    
    __tablename__ = "notifications"
    
    # Primary fields as specified
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    channel = Column(String(20), nullable=False)  # email, webpush, sms
    subscription_json = Column(JSON, nullable=True)  # Channel-specific subscription data
    last_sent_at = Column(DateTime, nullable=True)  # Last successful send
    
    # Additional useful fields
    story_id = Column(String, ForeignKey("stories.id"), nullable=True, index=True)
    status = Column(String(20), default="active")  # active, paused, failed
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="notifications")
    story = relationship("Story", back_populates="notifications")
    
    def __repr__(self):
        return f"<Notification(id={self.id}, user_id='{self.user_id}', channel='{self.channel}')>"