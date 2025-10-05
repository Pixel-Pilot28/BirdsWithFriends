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
    ScheduleStatus, ReleaseFrequency
)
from .database import Base, Story, Episode as EpisodeDB, GenerationLog, get_db, engine, SessionLocal
from .templates.manager import template_manager
from .llm.adapter import llm_adapter
from .scheduler import episode_scheduler

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


@app.on_event("shutdown")
async def shutdown_event():
    """Clean shutdown of services."""
    logger.info("Story Engine service shutting down")
    
    try:
        await episode_scheduler.stop()
        logger.info("Episode scheduler stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping episode scheduler: {e}")


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


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "story-engine",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "templates_loaded": len(template_manager.templates),
        "llm_adapter": "ready",
        "scheduler_running": episode_scheduler._running if episode_scheduler else False
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