"""
Story Engine Service - Main FastAPI service for story generation.

Provides REST endpoints for story creation, episode generation, and content management
with comprehensive age-appropriate content handling and safety features.
"""
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import logging

from fastapi import FastAPI, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, and_, or_
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel, Field

from .models import (
    StoryRequest, StoryResponse, Episode, StoryMetadata, 
    ContentFilter, validate_story_request, StoryScheduleRequest, 
    ScheduleStatus, ReleaseFrequency, PushSubscription, NotificationPreferences,
    NotificationType, NotificationStatus
)
from .database import (
    Base, Story, Episode as EpisodeDB, GenerationLog, get_db, engine, SessionLocal,
    PushSubscriptionDB, NotificationPreferencesDB, NotificationLogDB
)
from .templates.manager import template_manager
from .llm.adapter import llm_adapter
from .scheduler import episode_scheduler
from .notifications.email_sender import email_sender
from .notifications.webpush_sender import webpush_sender
from .notifications.notification_worker import notification_worker

logger = logging.getLogger(__name__)


class StoryEngineConfig:
    """Configuration for story engine service."""
    DATABASE_URL = "sqlite:///./story_engine.db"
    MAX_EPISODES_PER_STORY = 10
    MAX_CONCURRENT_GENERATIONS = 3
    DEFAULT_SAFETY_THRESHOLD = 0.8
    ENABLE_CONTENT_MODERATION = True


# Create tables
Base.metadata.create_all(bind=engine)


# FastAPI app
app = FastAPI(
    title="Birds with Friends - Story Engine",
    description="Generate age-appropriate bird stories with life lessons and entertainment",
    version="1.0.0"
)


class CreateStoryRequest(BaseModel):
    """Request to create a new story."""
    story_request: Dict[str, Any]
    # Optional scheduling parameters
    schedule: Optional[StoryScheduleRequest] = Field(None, description="Optional serialization schedule")


class GenerateEpisodeRequest(BaseModel):
    """Request to generate episodes for existing story."""
    episode_count: int = 1
    force_regenerate: bool = False


class StoryListResponse(BaseModel):
    """Response for listing stories."""
    stories: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup."""
    logger.info("Story Engine service starting up")
    
    # Ensure database tables exist
    Base.metadata.create_all(bind=engine)
    
    # Initialize template manager
    try:
        template_manager.reload_templates()
        logger.info("Templates loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load templates: {e}")
    
    # Start episode scheduler
    try:
        await episode_scheduler.start()
        logger.info("Episode scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start episode scheduler: {e}")
    
    # Start notification worker
    try:
        await notification_worker.start()
        logger.info("Notification worker started successfully")
    except Exception as e:
        logger.error(f"Failed to start notification worker: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean shutdown of services."""
    logger.info("Story Engine service shutting down")
    
    try:
        await episode_scheduler.stop()
        logger.info("Episode scheduler stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping episode scheduler: {e}")
    
    try:
        await notification_worker.stop()
        logger.info("Notification worker stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping notification worker: {e}")


@app.post("/stories", response_model=Dict[str, Any])
async def create_story(
    request: CreateStoryRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Create a new story from aggregated bird data.
    
    Validates the story request, creates story metadata, and optionally
    starts episode generation in the background.
    """
    try:
        # Validate story request
        story_request = validate_story_request(request.story_request)
        
        # Generate unique story ID
        story_id = str(uuid.uuid4())
        
        # Create story metadata
        story_metadata = Story(
            id=story_id,
            user_id=story_request.user_id,
            title=f"Bird Stories at Cornell Lab",  # Could be generated from content
            description=f"A {story_request.user_prefs.story_type} story featuring {len(story_request.characters)} bird characters",
            story_type=story_request.user_prefs.story_type,
            age_group=story_request.user_prefs.age_group,
            content_rating=story_request.user_prefs.content_rating,
            target_length=story_request.length,
            total_episodes=story_request.episodes,
            characters_data=[char.dict() for char in story_request.characters],
            species_data=[species.dict() for species in story_request.species_counts],
            user_preferences=story_request.user_prefs.dict(),
            time_range=story_request.time_range.dict()
        )
        
        db.add(story_metadata)
        db.commit()
        
        # Generate episodes based on scheduling preference
        episodes_to_generate = story_request.episodes if not request.schedule else 1
        
        # Start episode generation in background
        background_tasks.add_task(
            generate_episodes_background,
            story_id,
            story_request,
            episodes_to_generate  # Generate all episodes if not serialized, just first if serialized
        )
        
        # If scheduling is requested, set up the schedule after episode generation
        if request.schedule:
            # Update the schedule info in the request to use the story_id
            schedule_request = StoryScheduleRequest(
                story_id=story_id,
                start_date=request.schedule.start_date,
                release_frequency=request.schedule.release_frequency,
                timezone=request.schedule.timezone
            )
            
            background_tasks.add_task(
                setup_story_schedule_after_generation,
                story_id,
                schedule_request
            )
        
        logger.info(f"Created story {story_id} for user {story_request.user_id}")
        
        response = {
            "story_id": story_id,
            "status": "created",
            "total_episodes": story_request.episodes,
            "episodes_generated": 0,
            "estimated_completion": "2-5 minutes"
        }
        
        if request.schedule:
            response.update({
                "serialized": True,
                "start_date": request.schedule.start_date.isoformat(),
                "release_frequency": request.schedule.release_frequency.value,
                "timezone": request.schedule.timezone
            })
        
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid story request: {e}")
    except Exception as e:
        logger.error(f"Failed to create story: {e}")
        raise HTTPException(status_code=500, detail="Story creation failed")


@app.post("/stories/{story_id}/generate", response_model=Dict[str, Any])
async def generate_episodes(
    story_id: str,
    request: GenerateEpisodeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Generate episodes for an existing story.
    
    Can generate multiple episodes and handles regeneration of existing episodes.
    """
    # Get story
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Check episode limits
    if story.completed_episodes >= story.total_episodes and not request.force_regenerate:
        raise HTTPException(status_code=400, detail="All episodes already generated")
    
    episodes_to_generate = min(
        request.episode_count, 
        story.total_episodes - story.completed_episodes
    )
    
    if episodes_to_generate <= 0 and not request.force_regenerate:
        raise HTTPException(status_code=400, detail="No episodes to generate")
    
    # Reconstruct story request from stored data
    story_request_data = {
        "user_id": story.user_id,
        "time_range": story.time_range,
        "species_counts": story.species_data,
        "characters": story.characters_data,
        "user_prefs": story.user_preferences,
        "life_lessons": story.user_preferences.get("life_lessons", []),
        "length": story.target_length,
        "episodes": story.total_episodes
    }
    
    story_request = validate_story_request(story_request_data)
    
    # Start generation
    background_tasks.add_task(
        generate_episodes_background,
        story_id,
        story_request,
        episodes_to_generate
    )
    
    return {
        "story_id": story_id,
        "episodes_requested": episodes_to_generate,
        "status": "generating",
        "estimated_completion": f"{episodes_to_generate * 2}-{episodes_to_generate * 5} minutes"
    }


@app.get("/stories/{story_id}", response_model=Dict[str, Any])
async def get_story(story_id: str, db: Session = Depends(get_db)):
    """Get story metadata and episodes."""
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Get episodes
    episodes = db.query(EpisodeDB).filter(
        EpisodeDB.story_id == story_id
    ).order_by(EpisodeDB.episode_index).all()
    
    return {
        "story_id": story.id,
        "title": story.title,
        "description": story.description,
        "story_type": story.story_type,
        "age_group": story.age_group,
        "content_rating": story.content_rating,
        "created_at": story.created_at.isoformat(),
        "total_episodes": story.total_episodes,
        "completed_episodes": story.completed_episodes,
        "status": story.status,
        "episodes": [
            {
                "episode_index": ep.episode_index,
                "title": ep.title,
                "text": ep.text,
                "word_count": ep.word_count,
                "status": ep.status,
                "published_at": ep.published_at.isoformat() if ep.published_at else None,
                "safety_score": ep.safety_score,
                "content_warnings": ep.content_warnings or []
            }
            for ep in episodes
        ]
    }


@app.get("/stories/{story_id}/episodes/{episode_index}", response_model=Dict[str, Any])
async def get_episode(story_id: str, episode_index: int, db: Session = Depends(get_db)):
    """Get specific episode."""
    episode = db.query(EpisodeDB).filter(
        and_(
            EpisodeDB.story_id == story_id,
            EpisodeDB.episode_index == episode_index
        )
    ).first()
    
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    
    return {
        "episode_index": episode.episode_index,
        "title": episode.title,
        "text": episode.text,
        "summary": episode.summary,
        "word_count": episode.word_count,
        "tokens_used": episode.tokens_used,
        "generation_time": episode.generation_time,
        "safety_score": episode.safety_score,
        "content_warnings": episode.content_warnings or [],
        "status": episode.status,
        "created_at": episode.created_at.isoformat(),
        "published_at": episode.published_at.isoformat() if episode.published_at else None
    }


@app.get("/stories", response_model=StoryListResponse)
async def list_stories(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    story_type: Optional[str] = Query(None, description="Filter by story type"),
    age_group: Optional[str] = Query(None, description="Filter by age group"),
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """List stories with filtering and pagination."""
    query = db.query(Story)
    
    # Apply filters
    if user_id:
        query = query.filter(Story.user_id == user_id)
    if story_type:
        query = query.filter(Story.story_type == story_type)
    if age_group:
        query = query.filter(Story.age_group == age_group)
    if status:
        query = query.filter(Story.status == status)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    stories = query.order_by(Story.created_at.desc()).offset(offset).limit(page_size).all()
    
    return StoryListResponse(
        stories=[
            {
                "story_id": story.id,
                "title": story.title,
                "story_type": story.story_type,
                "age_group": story.age_group,
                "created_at": story.created_at.isoformat(),
                "total_episodes": story.total_episodes,
                "completed_episodes": story.completed_episodes,
                "status": story.status
            }
            for story in stories
        ],
        total=total,
        page=page,
        page_size=page_size
    )


@app.post("/stories/{story_id}/episodes/{episode_index}/publish")
async def publish_episode(
    story_id: str,
    episode_index: int,
    db: Session = Depends(get_db)
):
    """Publish an episode (change status from draft to published)."""
    episode = db.query(EpisodeDB).filter(
        and_(
            EpisodeDB.story_id == story_id,
            EpisodeDB.episode_index == episode_index
        )
    ).first()
    
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    
    if episode.status == "published":
        raise HTTPException(status_code=400, detail="Episode already published")
    
    # Check safety score
    if episode.safety_score < StoryEngineConfig.DEFAULT_SAFETY_THRESHOLD:
        raise HTTPException(
            status_code=400, 
            detail=f"Episode safety score ({episode.safety_score}) below threshold"
        )
    
    episode.status = "published"
    episode.published_at = datetime.now(timezone.utc)
    
    db.commit()
    
    return {"status": "published", "published_at": episode.published_at.isoformat()}


@app.get("/stories/{story_id}/stats")
async def get_story_stats(story_id: str, db: Session = Depends(get_db)):
    """Get statistics for a story."""
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    episodes = db.query(EpisodeDB).filter(EpisodeDB.story_id == story_id).all()
    
    stats = {
        "story_id": story_id,
        "total_episodes": story.total_episodes,
        "completed_episodes": len(episodes),
        "published_episodes": len([ep for ep in episodes if ep.status == "published"]),
        "total_words": sum(ep.word_count for ep in episodes),
        "total_tokens": sum(ep.tokens_used for ep in episodes),
        "average_safety_score": sum(ep.safety_score for ep in episodes) / len(episodes) if episodes else 0,
        "generation_time": sum(ep.generation_time for ep in episodes),
        "content_warnings": sum(len(ep.content_warnings or []) for ep in episodes)
    }
    
    return stats


@app.post("/stories/{story_id}/schedule")
async def schedule_story_release(
    story_id: str,
    request: StoryScheduleRequest,
    db: Session = Depends(get_db)
):
    """Schedule a story for serialized episode releases."""
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    if story.completed_episodes == 0:
        raise HTTPException(status_code=400, detail="Story must have at least one episode before scheduling")
    
    try:
        # Schedule episodes using the scheduler
        result = await episode_scheduler.schedule_story_episodes(
            story_id=story_id,
            start_date=request.start_date,
            release_frequency=request.release_frequency,
            user_timezone=request.timezone
        )
        
        return {
            "story_id": story_id,
            "scheduled": True,
            "start_date": request.start_date.isoformat(),
            "release_frequency": request.release_frequency.value,
            "timezone": request.timezone,
            **result
        }
        
    except Exception as e:
        logger.error(f"Failed to schedule story {story_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Scheduling failed: {e}")


@app.get("/stories/{story_id}/schedule")
async def get_story_schedule(story_id: str, db: Session = Depends(get_db)):
    """Get current schedule status for a story."""
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Get scheduled episodes
    scheduled_episodes = db.query(EpisodeDB).filter(
        and_(
            EpisodeDB.story_id == story_id,
            EpisodeDB.status == "scheduled"
        )
    ).count()
    
    return ScheduleStatus(
        story_id=story_id,
        is_serialized=story.is_serialized,
        total_episodes=story.total_episodes,
        published_episodes=story.completed_episodes,
        next_release_at=story.next_release_at,
        release_frequency=ReleaseFrequency(story.release_frequency) if story.release_frequency else ReleaseFrequency.DAILY,
        timezone=story.timezone
    ).dict()


@app.delete("/stories/{story_id}/schedule")
async def cancel_story_schedule(story_id: str, db: Session = Depends(get_db)):
    """Cancel scheduled releases for a story."""
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    if not story.is_serialized:
        raise HTTPException(status_code=400, detail="Story is not scheduled for serialized release")
    
    try:
        result = await episode_scheduler.cancel_story_schedule(story_id)
        return result
        
    except Exception as e:
        logger.error(f"Failed to cancel schedule for story {story_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Schedule cancellation failed: {e}")


@app.get("/scheduler/status")
async def get_scheduler_status():
    """Get current scheduler status and scheduled jobs."""
    try:
        jobs = episode_scheduler.get_scheduled_jobs()
        
        return {
            "scheduler_running": episode_scheduler._running,
            "total_scheduled_jobs": len(jobs),
            "jobs": jobs[:10],  # Return first 10 jobs to avoid large responses
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get scheduler status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get scheduler status")


# Ingest and Recognition endpoints

class SampleRequest(BaseModel):
    """Request for triggering sample capture."""
    source_url: Optional[str] = Field(None, description="Optional custom source URL")
    duration: Optional[int] = Field(None, description="Optional audio duration in seconds")


class RecognitionEvent(BaseModel):
    """Recognition event from audio/image services."""
    species: str = Field(..., description="Detected species name")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    timestamp: datetime = Field(..., description="Detection timestamp")
    source_type: str = Field(..., description="audio or image")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional detection metadata")


@app.post("/ingest/sample")
async def trigger_sample_capture(request: SampleRequest = SampleRequest()):
    """Trigger sampler to capture frame and audio (development endpoint)."""
    try:
        import httpx
        
        # Forward request to ingest service
        async with httpx.AsyncClient() as client:
            ingest_url = "http://localhost:8001/dev/ingest/test-sample"
            params = {}
            if request.source_url:
                params["source_url"] = request.source_url
            if request.duration:
                params["duration"] = request.duration
            
            response = await client.post(ingest_url, params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Ingest service error: {response.text}"
                )
    
    except httpx.RequestError as e:
        logger.error(f"Failed to connect to ingest service: {e}")
        raise HTTPException(
            status_code=503,
            detail="Ingest service unavailable. Make sure it's running on port 8001."
        )
    except Exception as e:
        logger.error(f"Sample capture failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/recognize")
async def receive_recognition_event(event: RecognitionEvent):
    """Receive recognition events from audio/image recognition services."""
    try:
        import httpx
        
        # Forward event to aggregator service
        async with httpx.AsyncClient() as client:
            aggregator_url = "http://localhost:8004/events"
            
            # Convert to aggregator expected format
            event_data = {
                "species": event.species,
                "confidence": event.confidence,
                "timestamp": event.timestamp.isoformat(),
                "source": event.source_type,
                "metadata": event.metadata
            }
            
            response = await client.post(aggregator_url, json=event_data)
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "Recognition event processed",
                    "event_id": response.json().get("event_id"),
                    "characters_updated": response.json().get("characters", [])
                }
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Aggregator service error: {response.text}"
                )
    
    except httpx.RequestError as e:
        logger.error(f"Failed to connect to aggregator service: {e}")
        raise HTTPException(
            status_code=503,
            detail="Aggregator service unavailable. Make sure it's running on port 8004."
        )
    except Exception as e:
        logger.error(f"Recognition event processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/aggregator/summary")
async def get_aggregation_summary(
    window_minutes: int = Query(15, ge=1, le=60, description="Aggregation window in minutes")
):
    """Get aggregated summary for the last window."""
    try:
        import httpx
        
        # Forward request to aggregator service
        async with httpx.AsyncClient() as client:
            aggregator_url = f"http://localhost:8004/summary?window_minutes={window_minutes}"
            
            response = await client.get(aggregator_url)
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Aggregator service error: {response.text}"
                )
    
    except httpx.RequestError as e:
        logger.error(f"Failed to connect to aggregator service: {e}")
        raise HTTPException(
            status_code=503,
            detail="Aggregator service unavailable. Make sure it's running on port 8004."
        )
    except Exception as e:
        logger.error(f"Failed to get aggregation summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Character management endpoints

class CharacterUpdate(BaseModel):
    """Update character archetype or name."""
    archetype: Optional[str] = Field(None, description="New archetype")
    name: Optional[str] = Field(None, description="New custom name")


@app.get("/characters")
async def list_characters(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    species: Optional[str] = Query(None, description="Filter by species"),
    active_only: bool = Query(True, description="Only return active characters"),
    limit: int = Query(50, ge=1, le=200, description="Maximum characters to return")
):
    """List characters with optional filtering."""
    try:
        import httpx
        
        # Forward request to aggregator service  
        async with httpx.AsyncClient() as client:
            params = {
                "limit": limit,
                "active_only": active_only
            }
            if user_id:
                params["user_id"] = user_id
            if species:
                params["species"] = species
            
            aggregator_url = "http://localhost:8004/characters"
            response = await client.get(aggregator_url, params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Aggregator service error: {response.text}"
                )
    
    except httpx.RequestError as e:
        logger.error(f"Failed to connect to aggregator service: {e}")
        raise HTTPException(
            status_code=503,
            detail="Aggregator service unavailable. Make sure it's running on port 8004."
        )
    except Exception as e:
        logger.error(f"Failed to list characters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/characters/{character_id}")
async def update_character(character_id: str, update: CharacterUpdate):
    """Update character archetype or name."""
    try:
        import httpx
        
        # Forward request to aggregator service
        async with httpx.AsyncClient() as client:
            aggregator_url = f"http://localhost:8004/characters/{character_id}"
            
            update_data = {}
            if update.archetype:
                update_data["archetype"] = update.archetype
            if update.name:
                update_data["name"] = update.name
            
            if not update_data:
                raise HTTPException(status_code=400, detail="No updates provided")
            
            response = await client.patch(aggregator_url, json=update_data)
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Aggregator service error: {response.text}"
                )
    
    except httpx.RequestError as e:
        logger.error(f"Failed to connect to aggregator service: {e}")
        raise HTTPException(
            status_code=503,
            detail="Aggregator service unavailable. Make sure it's running on port 8004."
        )
    except Exception as e:
        logger.error(f"Failed to update character: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/snapshots")
async def get_snapshots(limit: int = Query(10, ge=1, le=50, description="Number of snapshots to return")):
    """Get recent snapshots from aggregator service."""
    try:
        import httpx
        
        # Forward request to aggregator service
        async with httpx.AsyncClient() as client:
            aggregator_url = f"http://localhost:8004/snapshots?limit={limit}"
            
            response = await client.get(aggregator_url)
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Aggregator service error: {response.text}"
                )
    
    except httpx.RequestError as e:
        logger.error(f"Failed to connect to aggregator service: {e}")
        raise HTTPException(
            status_code=503,
            detail="Aggregator service unavailable. Make sure it's running on port 8004."
        )
    except Exception as e:
        logger.error(f"Failed to get snapshots: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# User management endpoints

class UserCreate(BaseModel):
    """Create new user."""
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: str = Field(..., description="User email address")
    preferences: Optional[Dict[str, Any]] = Field(default_factory=dict, description="User preferences")


class UserUpdate(BaseModel):
    """Update user information."""
    email: Optional[str] = Field(None, description="Updated email address")
    preferences: Optional[Dict[str, Any]] = Field(None, description="Updated preferences")


class UserResponse(BaseModel):
    """User information response."""
    id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    preferences: Dict[str, Any] = Field(..., description="User preferences")
    created_at: datetime = Field(..., description="Account creation time")
    updated_at: datetime = Field(..., description="Last update time")


@app.post("/users", response_model=Dict[str, Any])
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user account."""
    try:
        # Check if username already exists
        existing_user = db.query(NotificationPreferencesDB).filter(
            NotificationPreferencesDB.user_id == user.username
        ).first()
        
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")
        
        # Create user (using notification preferences as user storage for now)
        user_record = NotificationPreferencesDB(
            user_id=user.username,
            email_address=user.email,
            email_notifications=user.preferences.get("email_notifications", True),
            webpush_notifications=user.preferences.get("webpush_notifications", True)
        )
        
        db.add(user_record)
        db.commit()
        
        logger.info(f"Created user {user.username}")
        
        return {
            "id": user.username,
            "username": user.username,
            "email": user.email,
            "created_at": user_record.created_at.isoformat(),
            "message": "User created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        raise HTTPException(status_code=500, detail="User creation failed")


@app.get("/users/{user_id}", response_model=Dict[str, Any])
async def get_user(user_id: str, db: Session = Depends(get_db)):
    """Get user information."""
    user = db.query(NotificationPreferencesDB).filter(
        NotificationPreferencesDB.user_id == user_id
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user.user_id,
        "username": user.user_id,
        "email": user.email_address,
        "preferences": {
            "email_notifications": user.email_notifications,
            "webpush_notifications": user.webpush_notifications
        },
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat()
    }


@app.patch("/users/{user_id}/preferences")
async def update_user_preferences(
    user_id: str, 
    preferences: Dict[str, Any], 
    db: Session = Depends(get_db)
):
    """Update user preferences."""
    user = db.query(NotificationPreferencesDB).filter(
        NotificationPreferencesDB.user_id == user_id
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update notification preferences
    if "email_notifications" in preferences:
        user.email_notifications = preferences["email_notifications"]
    if "webpush_notifications" in preferences:
        user.webpush_notifications = preferences["webpush_notifications"]
    if "email_address" in preferences:
        user.email_address = preferences["email_address"]
    
    user.updated_at = datetime.now(timezone.utc)
    db.commit()
    
    logger.info(f"Updated preferences for user {user_id}")
    
    return {
        "success": True,
        "message": "Preferences updated successfully",
        "user_id": user_id,
        "updated_preferences": preferences
    }


# Notification endpoints

@app.post("/notifications/subscribe")
async def subscribe_to_push_notifications(
    subscription: PushSubscription,
    db: Session = Depends(get_db)
):
    """Subscribe to web push notifications."""
    try:
        # Remove existing subscription for same endpoint (if any)
        existing = db.query(PushSubscriptionDB).filter(
            and_(
                PushSubscriptionDB.user_id == subscription.user_id,
                PushSubscriptionDB.endpoint == subscription.endpoint
            )
        ).first()
        
        if existing:
            db.delete(existing)
        
        # Create new subscription
        new_subscription = PushSubscriptionDB(
            user_id=subscription.user_id,
            endpoint=subscription.endpoint,
            p256dh_key=subscription.p256dh_key,
            auth_key=subscription.auth_key
        )
        
        db.add(new_subscription)
        db.commit()
        
        logger.info(f"Web push subscription created for user {subscription.user_id}")
        
        return {
            "success": True,
            "message": "Successfully subscribed to push notifications",
            "user_id": subscription.user_id
        }
        
    except Exception as e:
        logger.error(f"Failed to create push subscription: {e}")
        raise HTTPException(status_code=500, detail="Subscription failed")


@app.get("/notifications/vapid-public-key")
async def get_vapid_public_key():
    """Get VAPID public key for web push subscriptions."""
    return {
        "publicKey": webpush_sender.get_vapid_public_key()
    }


@app.post("/notifications/preferences")
async def set_notification_preferences(
    preferences: NotificationPreferences,
    db: Session = Depends(get_db)
):
    """Set user notification preferences."""
    try:
        # Check if preferences already exist
        existing = db.query(NotificationPreferencesDB).filter(
            NotificationPreferencesDB.user_id == preferences.user_id
        ).first()
        
        if existing:
            # Update existing preferences
            existing.email_notifications = preferences.email_notifications
            existing.webpush_notifications = preferences.webpush_notifications
            existing.email_address = preferences.email_address
            existing.updated_at = datetime.now(timezone.utc)
        else:
            # Create new preferences
            new_prefs = NotificationPreferencesDB(
                user_id=preferences.user_id,
                email_notifications=preferences.email_notifications,
                webpush_notifications=preferences.webpush_notifications,
                email_address=preferences.email_address
            )
            db.add(new_prefs)
        
        db.commit()
        
        logger.info(f"Notification preferences updated for user {preferences.user_id}")
        
        return {
            "success": True,
            "message": "Notification preferences updated",
            "user_id": preferences.user_id
        }
        
    except Exception as e:
        logger.error(f"Failed to update notification preferences: {e}")
        raise HTTPException(status_code=500, detail="Failed to update preferences")


@app.get("/notifications/preferences/{user_id}")
async def get_notification_preferences(user_id: str, db: Session = Depends(get_db)):
    """Get user notification preferences."""
    preferences = db.query(NotificationPreferencesDB).filter(
        NotificationPreferencesDB.user_id == user_id
    ).first()
    
    if not preferences:
        # Return default preferences
        return {
            "user_id": user_id,
            "email_notifications": True,
            "webpush_notifications": True,
            "email_address": None
        }
    
    return {
        "user_id": preferences.user_id,
        "email_notifications": preferences.email_notifications,
        "webpush_notifications": preferences.webpush_notifications,
        "email_address": preferences.email_address
    }


@app.delete("/notifications/unsubscribe/{user_id}")
async def unsubscribe_all_notifications(user_id: str, db: Session = Depends(get_db)):
    """Unsubscribe user from all notifications."""
    try:
        # Remove all push subscriptions
        push_subscriptions = db.query(PushSubscriptionDB).filter(
            PushSubscriptionDB.user_id == user_id
        ).all()
        
        for subscription in push_subscriptions:
            db.delete(subscription)
        
        # Disable notification preferences
        preferences = db.query(NotificationPreferencesDB).filter(
            NotificationPreferencesDB.user_id == user_id
        ).first()
        
        if preferences:
            preferences.email_notifications = False
            preferences.webpush_notifications = False
            preferences.updated_at = datetime.now(timezone.utc)
        else:
            # Create disabled preferences
            new_prefs = NotificationPreferencesDB(
                user_id=user_id,
                email_notifications=False,
                webpush_notifications=False
            )
            db.add(new_prefs)
        
        db.commit()
        
        logger.info(f"User {user_id} unsubscribed from all notifications")
        
        return {
            "success": True,
            "message": "Successfully unsubscribed from all notifications",
            "user_id": user_id
        }
        
    except Exception as e:
        logger.error(f"Failed to unsubscribe user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Unsubscribe failed")


@app.post("/notifications/test/email/{user_id}")
async def send_test_email(user_id: str, db: Session = Depends(get_db)):
    """Send test email notification."""
    try:
        # Get user preferences
        preferences = db.query(NotificationPreferencesDB).filter(
            NotificationPreferencesDB.user_id == user_id
        ).first()
        
        if not preferences or not preferences.email_address:
            raise HTTPException(status_code=400, detail="No email address found for user")
        
        # Send test email
        result = await email_sender.send_test_email(preferences.email_address)
        
        return {
            "success": result["success"],
            "message": "Test email sent" if result["success"] else "Test email failed",
            "details": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Test email failed for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Test email failed")


@app.post("/notifications/test/webpush/{user_id}")
async def send_test_webpush(user_id: str, db: Session = Depends(get_db)):
    """Send test web push notification."""
    try:
        # Get user push subscriptions
        subscriptions = db.query(PushSubscriptionDB).filter(
            PushSubscriptionDB.user_id == user_id
        ).all()
        
        if not subscriptions:
            raise HTTPException(status_code=400, detail="No push subscriptions found for user")
        
        results = []
        
        for subscription in subscriptions:
            subscription_info = {
                "endpoint": subscription.endpoint,
                "keys": {
                    "p256dh": subscription.p256dh_key,
                    "auth": subscription.auth_key
                }
            }
            
            result = await webpush_sender.send_test_notification(subscription_info)
            results.append(result)
        
        success_count = sum(1 for r in results if r["success"])
        
        return {
            "success": success_count > 0,
            "message": f"Test push sent to {success_count}/{len(subscriptions)} subscriptions",
            "details": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Test web push failed for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Test web push failed")


@app.get("/notifications/logs/{user_id}")
async def get_notification_logs(
    user_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get notification delivery logs for user."""
    logs = db.query(NotificationLogDB).filter(
        NotificationLogDB.user_id == user_id
    ).order_by(NotificationLogDB.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": log.id,
            "story_id": log.story_id,
            "episode_index": log.episode_index,
            "notification_type": log.notification_type,
            "status": log.status,
            "attempts": log.attempts,
            "error_message": log.error_message,
            "created_at": log.created_at.isoformat(),
            "sent_at": log.sent_at.isoformat() if log.sent_at else None
        }
        for log in logs
    ]


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "story-engine",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "templates_loaded": len(template_manager.templates),
        "llm_adapter": "ready",
        "scheduler_running": episode_scheduler._running if episode_scheduler else False,
        "notification_worker_running": notification_worker.running if notification_worker else False,
        "vapid_public_key_available": bool(webpush_sender.public_key_base64) if webpush_sender else False
    }


async def generate_episodes_background(
    story_id: str,
    story_request: StoryRequest,
    episode_count: int
):
    """Background task to generate episodes."""
    db = SessionLocal()
    
    try:
        story = db.query(Story).filter(Story.id == story_id).first()
        if not story:
            logger.error(f"Story {story_id} not found for episode generation")
            return
        
        for i in range(episode_count):
            episode_index = story.completed_episodes + i + 1
            
            if episode_index > story.total_episodes:
                break
            
            try:
                # Generate episode
                episode_response = await generate_single_episode(story_request, episode_index)
                
                # Create episode record
                episode = EpisodeDB(
                    story_id=story_id,
                    episode_index=episode_index,
                    title=f"Episode {episode_index}",
                    text=episode_response.episode_text,
                    word_count=len(episode_response.episode_text.split()),
                    tokens_used=episode_response.tokens,
                    generation_time=episode_response.generation_time,
                    safety_score=episode_response.safety_score,
                    content_warnings=episode_response.content_warnings,
                    template_used=getattr(episode_response, 'template_name', None),
                    status="draft"
                )
                
                db.add(episode)
                
                # Update story progress
                story.completed_episodes += 1
                story.total_tokens_used += episode_response.tokens
                
                # Update average safety score
                if story.completed_episodes == 1:
                    story.average_safety_score = episode_response.safety_score
                else:
                    story.average_safety_score = (
                        story.average_safety_score * (story.completed_episodes - 1) + 
                        episode_response.safety_score
                    ) / story.completed_episodes
                
                db.commit()
                
                logger.info(f"Generated episode {episode_index} for story {story_id}")
                
            except Exception as e:
                logger.error(f"Failed to generate episode {episode_index} for story {story_id}: {e}")
                db.rollback()
                continue
        
        # Mark story as completed if all episodes generated
        if story.completed_episodes >= story.total_episodes:
            story.status = "completed"
            db.commit()
            
    except Exception as e:
        logger.error(f"Background episode generation failed for story {story_id}: {e}")
    finally:
        db.close()


async def generate_single_episode(story_request: StoryRequest, episode_index: int) -> StoryResponse:
    """Generate a single episode."""
    try:
        # Get appropriate template
        template = template_manager.get_template(story_request)
        
        # Fill template with story data
        filled_template = template_manager.fill_template(template, story_request)
        
        # Generate story using LLM
        response = await llm_adapter.generate_story(story_request, filled_template)
        
        logger.info(f"Generated episode {episode_index}: {response.tokens} tokens, safety score {response.safety_score}")
        
        return response
        
    except Exception as e:
        logger.error(f"Episode generation failed: {e}")
        raise


async def setup_story_schedule_after_generation(
    story_id: str,
    schedule_request: StoryScheduleRequest
):
    """Background task to set up story scheduling after all episodes are generated."""
    
    # Wait for episodes to be generated (check every 30 seconds for up to 10 minutes)
    max_wait_time = 600  # 10 minutes
    check_interval = 30   # 30 seconds
    waited_time = 0
    
    db = SessionLocal()
    
    try:
        while waited_time < max_wait_time:
            story = db.query(Story).filter(Story.id == story_id).first()
            if not story:
                logger.error(f"Story {story_id} not found for scheduling setup")
                return
            
            # Check if all episodes are generated
            if story.completed_episodes >= story.total_episodes:
                # All episodes generated, set up the schedule
                try:
                    result = await episode_scheduler.schedule_story_episodes(
                        story_id=story_id,
                        start_date=schedule_request.start_date,
                        release_frequency=schedule_request.release_frequency,
                        user_timezone=schedule_request.timezone
                    )
                    
                    logger.info(f"Successfully scheduled story {story_id}: {result}")
                    return
                    
                except Exception as e:
                    logger.error(f"Failed to schedule story {story_id}: {e}")
                    return
            
            # Wait before checking again
            await asyncio.sleep(check_interval)
            waited_time += check_interval
        
        logger.warning(f"Timeout waiting for story {story_id} episodes to be generated for scheduling")
        
    except Exception as e:
        logger.error(f"Error in setup_story_schedule_after_generation for story {story_id}: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
