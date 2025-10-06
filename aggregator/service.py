"""
Event Aggregation Service.

Collects recognition events from multiple sources, manages character instances,
and provides sliding window aggregation for story generation.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import get_db, engine, SessionLocal
from .character_manager import character_manager
from .models import Character, RecognitionEventDB, AggregationSummary
from shared.database.models import RecognitionEvent, Snapshot

logger = logging.getLogger(__name__)


class StoryInput(BaseModel):
    """Story generation input payload."""
    characters: List[Dict[str, Any]]
    species: List[str]
    recent_activity: List[Dict[str, Any]]
    timeframe: Dict[str, str]
    location: str = "Cornell Lab feeder"


class AggregationConfig:
    """Configuration for aggregation windows."""
    WINDOW_SIZE_MINUTES = 15  # Sliding window size
    CLEANUP_INTERVAL_HOURS = 24  # How often to clean old events
    MAX_CHARACTERS_PER_STORY = 5  # Limit characters in story
    MIN_CONFIDENCE_THRESHOLD = 0.7  # Skip low confidence detections


class AggregatorService:
    """Main aggregation service."""
    
    def __init__(self):
        self.config = AggregationConfig()
        self.event_buffer = deque(maxlen=1000)  # In-memory event buffer
        self.running = False
    
    def start_background_processing(self):
        """Start background event processing."""
        self.running = True
        logger.info("Aggregator service started")
    
    def stop_background_processing(self):
        """Stop background event processing."""
        self.running = False
        logger.info("Aggregator service stopped")
    
    async def process_recognition_event(
        self, 
        event_data: Dict[str, Any],
        db: Session
    ) -> List[Character]:
        """
        Process a new recognition event.
        
        Args:
            event_data: Recognition event from audio/image service
            db: Database session
            
        Returns:
            List of created/updated characters
        """
        try:
            # Add to event buffer for sliding window
            event_data['processed_at'] = datetime.now(timezone.utc).isoformat()
            self.event_buffer.append(event_data)
            
            # Create/update characters
            characters = character_manager.create_characters_from_event(db, event_data)
            
            logger.info(
                f"Processed event from {event_data['source']}: "
                f"{len(event_data.get('detections', []))} detections, "
                f"{len(characters)} characters affected"
            )
            
            return characters
            
        except Exception as e:
            logger.error(f"Failed to process recognition event: {e}")
            raise HTTPException(status_code=500, detail=f"Event processing failed: {e}")
    
    def get_aggregated_summary(
        self,
        db: Session,
        since: Optional[datetime] = None,
        window_minutes: Optional[int] = None
    ) -> StoryInput:
        """
        Generate aggregated summary for story generation.
        
        Args:
            db: Database session
            since: Start time for aggregation (default: 15 minutes ago)
            window_minutes: Aggregation window size (default: 15 minutes)
            
        Returns:
            StoryInput payload for story generation
        """
        if since is None:
            window_minutes = window_minutes or self.config.WINDOW_SIZE_MINUTES
            since = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        
        end_time = datetime.now(timezone.utc)
        
        # Get active characters in timeframe
        active_characters = character_manager.get_active_characters_in_timeframe(
            db, since, end_time
        )
        
        # Get recent recognition events
        recent_events = (
            db.query(RecognitionEventDB)
            .filter(RecognitionEventDB.timestamp >= since)
            .order_by(RecognitionEventDB.timestamp.desc())
            .all()
        )
        
        # Aggregate species activity
        species_activity = self._aggregate_species_activity(recent_events)
        
        # Limit characters for story coherence
        characters_for_story = active_characters[:self.config.MAX_CHARACTERS_PER_STORY]
        
        # Format characters for story generation
        character_data = []
        for char in characters_for_story:
            character_data.append({
                "id": char.id,
                "species": char.species,
                "archetype": char.archetype,
                "appearance_count": char.appearance_count,
                "first_seen": char.first_seen.isoformat(),
                "last_seen": char.last_seen.isoformat(),
                "name": None,  # Not implemented yet
                "personality_notes": char.notes
            })
        
        # Format recent activity
        activity_data = []
        for event in recent_events[:20]:  # Limit recent activity
            activity_data.append({
                "timestamp": event.timestamp.isoformat(),
                "source": event.source,
                "species": event.species,
                "count": event.count,
                "confidence": event.confidence,
                "character_id": event.character_id
            })
        
        # Create story input payload
        story_input = StoryInput(
            characters=character_data,
            species=list(species_activity.keys()),
            recent_activity=activity_data,
            timeframe={
                "start": since.isoformat(),
                "end": end_time.isoformat(),
                "window_minutes": str(int((end_time - since).total_seconds() / 60))
            }
        )
        
        # Store aggregation summary
        self._store_aggregation_summary(db, since, end_time, story_input)
        
        return story_input
    
    def _aggregate_species_activity(
        self, 
        events: List[RecognitionEventDB]
    ) -> Dict[str, Dict[str, Any]]:
        """Aggregate species-level activity metrics."""
        species_stats = defaultdict(lambda: {
            'total_detections': 0,
            'total_count': 0,
            'avg_confidence': 0.0,
            'sources': set(),
            'last_seen': None
        })
        
        for event in events:
            stats = species_stats[event.species]
            stats['total_detections'] += 1
            stats['total_count'] += event.count
            stats['sources'].add(event.source)
            
            # Update average confidence
            prev_avg = stats['avg_confidence']
            stats['avg_confidence'] = (
                prev_avg * (stats['total_detections'] - 1) + event.confidence
            ) / stats['total_detections']
            
            # Update last seen
            if stats['last_seen'] is None or event.timestamp > stats['last_seen']:
                stats['last_seen'] = event.timestamp
        
        # Convert sets to lists for JSON serialization
        for species in species_stats:
            species_stats[species]['sources'] = list(species_stats[species]['sources'])
            if species_stats[species]['last_seen']:
                species_stats[species]['last_seen'] = species_stats[species]['last_seen'].isoformat()
        
        return dict(species_stats)
    
    def _store_aggregation_summary(
        self,
        db: Session,
        start_time: datetime,
        end_time: datetime,
        story_input: StoryInput
    ):
        """Store aggregation summary in database."""
        try:
            summary = AggregationSummary(
                start_time=start_time,
                end_time=end_time,
                character_count=len(story_input.characters),
                species_count=len(story_input.species),
                event_count=len(story_input.recent_activity),
                summary_data=story_input.dict()
            )
            
            db.add(summary)
            db.commit()
            
            logger.debug(f"Stored aggregation summary: {start_time} - {end_time}")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to store aggregation summary: {e}")
    
    async def cleanup_old_events(self, db: Session, hours_ago: int = 24):
        """Clean up old recognition events."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
        
        deleted_count = (
            db.query(RecognitionEventDB)
            .filter(RecognitionEventDB.timestamp < cutoff_time)
            .delete()
        )
        
        db.commit()
        logger.info(f"Cleaned up {deleted_count} old recognition events")


# Global aggregator service instance
aggregator_service = AggregatorService()


# FastAPI app for aggregator service
app = FastAPI(
    title="Birds with Friends - Event Aggregator",
    description="Collects recognition events and provides aggregated summaries for story generation",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup."""
    # Create database tables
    from .models import Base
    Base.metadata.create_all(bind=engine)
    
    # Start background processing
    aggregator_service.start_background_processing()
    
    logger.info("Aggregator service started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    aggregator_service.stop_background_processing()
    logger.info("Aggregator service stopped")


@app.post("/events", response_model=Dict[str, Any])
async def receive_recognition_event(
    event_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Receive and process recognition events from audio/image services.
    
    Expected event format matches recognition service output.
    """
    try:
        characters = await aggregator_service.process_recognition_event(event_data, db)
        
        return {
            "status": "processed",
            "characters_affected": len(characters),
            "character_ids": [c.id for c in characters]
        }
        
    except Exception as e:
        logger.error(f"Failed to process event: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/summary", response_model=StoryInput)
async def get_aggregation_summary(
    since: Optional[str] = Query(None, description="Start time (ISO format)"),
    window_minutes: Optional[int] = Query(15, description="Aggregation window in minutes"),
    db: Session = Depends(get_db)
):
    """
    Get aggregated summary for story generation.
    
    Returns story input payload with characters, species, and recent activity.
    """
    try:
        # Parse since parameter
        since_dt = None
        if since:
            since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
        
        story_input = aggregator_service.get_aggregated_summary(
            db, since_dt, window_minutes
        )
        
        return story_input
        
    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/characters", response_model=List[Dict[str, Any]])
async def get_characters(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    species: Optional[str] = Query(None, description="Filter by species"),
    archetype: Optional[str] = Query(None, description="Filter by archetype"),
    db: Session = Depends(get_db)
):
    """Get list of characters with optional filtering."""
    try:
        characters = character_manager.get_characters(
            db, skip, limit, species, archetype
        )
        
        return [
            {
                "id": c.id,
                "species": c.species,
                "archetype": c.archetype,
                "appearance_count": c.appearance_count,
                "first_seen": c.first_seen.isoformat(),
                "last_seen": c.last_seen.isoformat(),
                "name": None,  # Not implemented yet
                "personality_notes": c.notes
            }
            for c in characters
        ]
        
    except Exception as e:
        logger.error(f"Failed to get characters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/characters/{character_id}", response_model=Dict[str, Any])
async def get_character(
    character_id: str,
    db: Session = Depends(get_db)
):
    """Get specific character by ID."""
    character = character_manager.get_character_by_id(db, character_id)
    
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    return {
        "id": character.id,
        "species": character.species,
        "archetype": character.archetype,
        "appearance_count": character.appearance_count,
        "first_seen": character.first_seen.isoformat(),
        "last_seen": character.last_seen.isoformat(),
        "name": None,  # Not implemented yet
        "personality_notes": character.notes
    }


@app.patch("/characters/{character_id}", response_model=Dict[str, Any])
async def update_character(
    character_id: str,
    updates: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Update character information."""
    from .models import CharacterUpdate
    
    try:
        character_update = CharacterUpdate(**updates)
        updated_character = character_manager.update_character(
            db, character_id, character_update
        )
        
        if not updated_character:
            raise HTTPException(status_code=404, detail="Character not found")
        
        return {
            "id": updated_character.id,
            "species": updated_character.species,
            "archetype": updated_character.archetype,
            "appearance_count": updated_character.appearance_count,
            "first_seen": updated_character.first_seen.isoformat(),
            "last_seen": updated_character.last_seen.isoformat(),
            "name": None,  # Not implemented yet
            "personality_notes": updated_character.notes
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update character: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats", response_model=Dict[str, Any])
async def get_system_stats(db: Session = Depends(get_db)):
    """Get system statistics."""
    try:
        # Character count by species
        species_counts = character_manager.get_character_count_by_species(db)
        
        # Total counts
        total_characters = sum(species_counts.values())
        
        # Recent activity (last hour)
        since_hour = datetime.now(timezone.utc) - timedelta(hours=1)
        recent_events = (
            db.query(RecognitionEventDB)
            .filter(RecognitionEventDB.timestamp >= since_hour)
            .count()
        )
        
        return {
            "total_characters": total_characters,
            "species_counts": species_counts,
            "recent_events_1h": recent_events,
            "buffer_size": len(aggregator_service.event_buffer),
            "service_status": "running" if aggregator_service.running else "stopped"
        }
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/snapshots")
async def get_snapshots(limit: int = 10):
    """Get recent snapshots from recognition events."""
    try:
        db = SessionLocal()
        
        # Get recent recognition events with snapshots
        events = db.query(RecognitionEvent)\
            .join(Snapshot)\
            .order_by(RecognitionEvent.timestamp.desc())\
            .limit(limit)\
            .all()
        
        snapshots = []
        for event in events:
            for snapshot in event.snapshots:
                snapshots.append({
                    "id": str(snapshot.id),
                    "image_url": snapshot.url,
                    "audio_url": None,  # Add audio URL if available
                    "timestamp": event.timestamp.isoformat(),
                    "detections": [{
                        "species": event.species,
                        "confidence": event.confidence,
                        "bounding_box": None  # Add if bounding box data available
                    }] if event.species else []
                })
        
        return snapshots[:limit]
    
    except Exception as e:
        logger.error(f"Failed to get snapshots: {e}")
        # Return empty list if no data available yet
        return []
    finally:
        if 'db' in locals():
            db.close()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "aggregator",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)