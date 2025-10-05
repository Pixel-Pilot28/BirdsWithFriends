"""
Character management system.

Handles character placeholder creation, updates, and lifecycle management.
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from .models import Character, RecognitionEventDB, CharacterResponse, CharacterUpdate
from .archetype_mapper import archetype_mapper
from .database import get_db

logger = logging.getLogger(__name__)


class CharacterManager:
    """Manages character creation and lifecycle."""
    
    def __init__(self):
        self.archetype_mapper = archetype_mapper
    
    def create_characters_from_event(
        self, 
        db: Session,
        event_data: Dict[str, Any]
    ) -> List[Character]:
        """
        Create character placeholders from a recognition event.
        
        Args:
            db: Database session
            event_data: Recognition event data
            
        Returns:
            List of created Character objects
        """
        created_characters = []
        
        # Extract event information
        detections = event_data.get('detections', [])
        timestamp_str = event_data.get('timestamp')
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        
        # Store the recognition event
        for detection in detections:
            species = detection['species']
            count = detection.get('count', 1)
            confidence = detection.get('confidence', 0.0)
            low_confidence = detection.get('low_confidence', False)
            bbox = detection.get('bbox')
            
            # Store recognition event in database
            event_record = RecognitionEventDB(
                timestamp=timestamp,
                source=event_data['source'],
                species=species,
                count=count,
                confidence=confidence,
                low_confidence=low_confidence,
                bbox=bbox,
                snapshot_url=event_data.get('snapshot_url')
            )
            db.add(event_record)
            
            # Create character placeholders for multi-count detections
            if count > 1:
                characters = self._create_character_instances(
                    db=db,
                    species=species,
                    count=count,
                    timestamp=timestamp,
                    event_record=event_record
                )
                created_characters.extend(characters)
            
            # For single count, still update existing character if it exists
            elif count == 1:
                character = self._update_or_create_single_character(
                    db=db,
                    species=species,
                    timestamp=timestamp,
                    event_record=event_record
                )
                if character:
                    created_characters.append(character)
        
        # Commit all changes
        try:
            db.commit()
            logger.info(f"Created {len(created_characters)} character records")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create characters: {e}")
            raise
        
        return created_characters
    
    def _create_character_instances(
        self,
        db: Session,
        species: str,
        count: int,
        timestamp: datetime,
        event_record: RecognitionEventDB
    ) -> List[Character]:
        """Create multiple character instances for a species."""
        characters = []
        
        for i in range(1, count + 1):
            character_id = self._generate_character_id(species, i)
            
            # Check if character already exists
            existing = db.query(Character).filter(Character.id == character_id).first()
            
            if existing:
                # Update existing character
                existing.last_seen = timestamp
                existing.appearance_count += 1
                characters.append(existing)
                
                # Link event to character
                event_record.character_id = character_id
                
                logger.debug(f"Updated existing character: {character_id}")
            else:
                # Create new character
                archetype = self.archetype_mapper.get_archetype(species)
                
                character = Character(
                    id=character_id,
                    species=species,
                    archetype=archetype,
                    first_seen=timestamp,
                    last_seen=timestamp,
                    appearance_count=1
                )
                
                db.add(character)
                characters.append(character)
                
                # Link event to character
                event_record.character_id = character_id
                
                logger.debug(f"Created new character: {character_id}")
        
        return characters
    
    def _update_or_create_single_character(
        self,
        db: Session,
        species: str,
        timestamp: datetime,
        event_record: RecognitionEventDB
    ) -> Optional[Character]:
        """Update or create a single character for a species."""
        # For single counts, we can either:
        # 1. Update an existing character of this species
        # 2. Create a new character if none exist
        
        # Find the most recent character of this species
        existing = (
            db.query(Character)
            .filter(Character.species == species)
            .order_by(Character.last_seen.desc())
            .first()
        )
        
        if existing:
            # Update existing character
            existing.last_seen = timestamp
            existing.appearance_count += 1
            event_record.character_id = existing.id
            return existing
        else:
            # Create new character with index 1
            character_id = self._generate_character_id(species, 1)
            archetype = self.archetype_mapper.get_archetype(species)
            
            character = Character(
                id=character_id,
                species=species,
                archetype=archetype,
                first_seen=timestamp,
                last_seen=timestamp,
                appearance_count=1
            )
            
            db.add(character)
            event_record.character_id = character_id
            
            logger.debug(f"Created new single character: {character_id}")
            return character
    
    def _generate_character_id(self, species: str, index: int) -> str:
        """Generate character ID from species name and index."""
        import re
        
        # Convert to lowercase, replace spaces with underscores, remove special chars
        clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', species.lower())
        clean_name = re.sub(r'\s+', '_', clean_name.strip())
        return f"{clean_name}_{index}"
    
    def get_character_by_id(self, db: Session, character_id: str) -> Optional[Character]:
        """Get character by ID."""
        return db.query(Character).filter(Character.id == character_id).first()
    
    def get_characters(
        self, 
        db: Session,
        skip: int = 0,
        limit: int = 100,
        species_filter: Optional[str] = None,
        archetype_filter: Optional[str] = None
    ) -> List[Character]:
        """
        Get list of characters with optional filtering.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            species_filter: Filter by species
            archetype_filter: Filter by archetype
            
        Returns:
            List of Character objects
        """
        query = db.query(Character)
        
        if species_filter:
            query = query.filter(Character.species.ilike(f"%{species_filter}%"))
        
        if archetype_filter:
            query = query.filter(Character.archetype == archetype_filter)
        
        return query.order_by(Character.last_seen.desc()).offset(skip).limit(limit).all()
    
    def update_character(
        self, 
        db: Session, 
        character_id: str, 
        updates: CharacterUpdate
    ) -> Optional[Character]:
        """
        Update character information.
        
        Args:
            db: Database session
            character_id: Character ID
            updates: Updates to apply
            
        Returns:
            Updated Character object or None if not found
        """
        character = self.get_character_by_id(db, character_id)
        
        if not character:
            return None
        
        # Apply updates
        update_data = updates.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(character, field, value)
        
        try:
            db.commit()
            logger.info(f"Updated character {character_id}")
            return character
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update character {character_id}: {e}")
            raise
    
    def get_active_characters_in_timeframe(
        self,
        db: Session,
        start_time: datetime,
        end_time: datetime
    ) -> List[Character]:
        """
        Get characters that were active in a specific timeframe.
        
        Args:
            db: Database session
            start_time: Start of timeframe
            end_time: End of timeframe
            
        Returns:
            List of active Character objects
        """
        return (
            db.query(Character)
            .filter(
                and_(
                    Character.last_seen >= start_time,
                    Character.first_seen <= end_time
                )
            )
            .order_by(Character.appearance_count.desc())
            .all()
        )
    
    def get_character_count_by_species(self, db: Session) -> Dict[str, int]:
        """
        Get count of characters by species.
        
        Returns:
            Dictionary mapping species to character count
        """
        from sqlalchemy import func
        
        results = (
            db.query(Character.species, func.count(Character.id))
            .group_by(Character.species)
            .all()
        )
        
        return {species: count for species, count in results}


# Global character manager instance
character_manager = CharacterManager()