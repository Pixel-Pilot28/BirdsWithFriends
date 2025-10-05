"""
CRUD operations for Birds with Friends database models.

Provides basic Create, Read, Update, Delete operations for all tables.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from .models import User, RecognitionEvent, Snapshot, Character, Story, Episode, Notification
from .config import get_session


class BaseCRUD:
    """Base class for CRUD operations."""
    
    def __init__(self, model):
        self.model = model
    
    def create(self, db: Session, **kwargs) -> Any:
        """Create a new record."""
        obj = self.model(**kwargs)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj
    
    def get(self, db: Session, id: Any) -> Optional[Any]:
        """Get record by ID."""
        return db.query(self.model).filter(self.model.id == id).first()
    
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> List[Any]:
        """Get multiple records with pagination."""
        return db.query(self.model).offset(skip).limit(limit).all()
    
    def update(self, db: Session, id: Any, **kwargs) -> Optional[Any]:
        """Update record by ID."""
        obj = self.get(db, id)
        if obj:
            for key, value in kwargs.items():
                setattr(obj, key, value)
            db.commit()
            db.refresh(obj)
        return obj
    
    def delete(self, db: Session, id: Any) -> bool:
        """Delete record by ID."""
        obj = self.get(db, id)
        if obj:
            db.delete(obj)
            db.commit()
            return True
        return False


# CRUD Classes for each model

class UserCRUD(BaseCRUD):
    """CRUD operations for User table."""
    
    def __init__(self):
        super().__init__(User)
    
    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        """Get user by email address."""
        return db.query(User).filter(User.email == email).first()
    
    def create_user(self, db: Session, id: str, email: str = None, phone: str = None, 
                   timezone: str = "UTC", preferences: Dict = None) -> User:
        """Create a new user with validation."""
        return self.create(
            db,
            id=id,
            email=email,
            phone=phone,
            timezone=timezone,
            preferences_json=preferences or {}
        )


class RecognitionEventCRUD(BaseCRUD):
    """CRUD operations for RecognitionEvent table."""
    
    def __init__(self):
        super().__init__(RecognitionEvent)
    
    def create_event(self, db: Session, payload: Dict[str, Any]) -> RecognitionEvent:
        """Create a new recognition event."""
        return self.create(db, payload_json=payload)
    
    def get_recent(self, db: Session, hours: int = 24, limit: int = 100) -> List[RecognitionEvent]:
        """Get recent recognition events."""
        cutoff = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        return (db.query(RecognitionEvent)
                .filter(RecognitionEvent.created_at >= cutoff)
                .order_by(desc(RecognitionEvent.created_at))
                .limit(limit)
                .all())


class SnapshotCRUD(BaseCRUD):
    """CRUD operations for Snapshot table."""
    
    def __init__(self):
        super().__init__(Snapshot)
    
    def create_snapshot(self, db: Session, id: str, url: str, 
                       source_event_id: int = None) -> Snapshot:
        """Create a new snapshot."""
        return self.create(
            db,
            id=id,
            url=url,
            source_event_id=source_event_id
        )
    
    def get_by_event(self, db: Session, event_id: int) -> List[Snapshot]:
        """Get snapshots for a specific recognition event."""
        return db.query(Snapshot).filter(Snapshot.source_event_id == event_id).all()


class CharacterCRUD(BaseCRUD):
    """CRUD operations for Character table."""
    
    def __init__(self):
        super().__init__(Character)
    
    def create_character(self, db: Session, id: str, species: str, archetype: str = None,
                        placeholder: bool = False) -> Character:
        """Create a new character."""
        return self.create(
            db,
            id=id,
            species=species,
            archetype=archetype,
            placeholder_bool=placeholder
        )
    
    def get_by_species(self, db: Session, species: str) -> List[Character]:
        """Get all characters of a specific species."""
        return db.query(Character).filter(Character.species == species).all()
    
    def get_active(self, db: Session) -> List[Character]:
        """Get non-placeholder characters."""
        return db.query(Character).filter(Character.placeholder_bool == False).all()
    
    def update_last_seen(self, db: Session, id: str) -> Optional[Character]:
        """Update character's last seen timestamp."""
        return self.update(db, id, last_seen=datetime.utcnow())


class StoryCRUD(BaseCRUD):
    """CRUD operations for Story table."""
    
    def __init__(self):
        super().__init__(Story)
    
    def create_story(self, db: Session, id: str, user_id: str, title: str,
                    total_episodes: int = 1, release_frequency: str = "daily") -> Story:
        """Create a new story."""
        return self.create(
            db,
            id=id,
            user_id=user_id,
            title=title,
            total_episodes=total_episodes,
            release_frequency=release_frequency
        )
    
    def get_by_user(self, db: Session, user_id: str, status: str = None) -> List[Story]:
        """Get stories for a specific user."""
        query = db.query(Story).filter(Story.user_id == user_id)
        if status:
            query = query.filter(Story.status == status)
        return query.order_by(desc(Story.created_at)).all()
    
    def get_published(self, db: Session, limit: int = 50) -> List[Story]:
        """Get published stories."""
        return (db.query(Story)
                .filter(Story.status == "published")
                .order_by(desc(Story.created_at))
                .limit(limit)
                .all())


class EpisodeCRUD(BaseCRUD):
    """CRUD operations for Episode table."""
    
    def __init__(self):
        super().__init__(Episode)
    
    def create_episode(self, db: Session, id: str, story_id: str, index: int, 
                      text: str) -> Episode:
        """Create a new episode."""
        return self.create(
            db,
            id=id,
            story_id=story_id,
            index=index,
            text=text
        )
    
    def get_by_story(self, db: Session, story_id: str) -> List[Episode]:
        """Get all episodes for a story."""
        return (db.query(Episode)
                .filter(Episode.story_id == story_id)
                .order_by(Episode.index)
                .all())
    
    def publish_episode(self, db: Session, id: str) -> Optional[Episode]:
        """Publish an episode."""
        return self.update(
            db, 
            id, 
            status="published",
            published_at=datetime.utcnow()
        )


class NotificationCRUD(BaseCRUD):
    """CRUD operations for Notification table."""
    
    def __init__(self):
        super().__init__(Notification)
    
    def create_notification(self, db: Session, user_id: str, channel: str,
                           subscription_data: Dict = None, story_id: str = None) -> Notification:
        """Create a new notification subscription."""
        return self.create(
            db,
            user_id=user_id,
            channel=channel,
            subscription_json=subscription_data or {},
            story_id=story_id
        )
    
    def get_by_user(self, db: Session, user_id: str, channel: str = None) -> List[Notification]:
        """Get notifications for a user, optionally filtered by channel."""
        query = db.query(Notification).filter(Notification.user_id == user_id)
        if channel:
            query = query.filter(Notification.channel == channel)
        return query.all()
    
    def update_last_sent(self, db: Session, id: int) -> Optional[Notification]:
        """Update last sent timestamp."""
        return self.update(db, id, last_sent_at=datetime.utcnow())


# Global CRUD instances
user_crud = UserCRUD()
recognition_event_crud = RecognitionEventCRUD()
snapshot_crud = SnapshotCRUD()
character_crud = CharacterCRUD()
story_crud = StoryCRUD()
episode_crud = EpisodeCRUD()
notification_crud = NotificationCRUD()