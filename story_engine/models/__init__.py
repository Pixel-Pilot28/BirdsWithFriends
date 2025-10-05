"""
Story Engine Models - Pydantic schemas for story generation.

Defines comprehensive models for story requests, episodes, and all related data structures
with proper validation, age-appropriate content handling, and safety constraints.
"""
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union, Literal
from enum import Enum
from pydantic import BaseModel, Field, validator, root_validator
import re


class AgeGroup(str, Enum):
    """Supported age groups for story generation."""
    CHILD = "child"
    ADULT = "adult"
    TODDLER = "toddler"  # ages 2-4
    PRESCHOOL = "preschool"  # ages 4-6
    SCHOOL_AGE = "school_age"  # ages 6-12
    TEEN = "teen"  # ages 13-17


class StoryLength(str, Enum):
    """Story length options."""
    SHORT = "short"      # ~100-200 words
    MEDIUM = "medium"    # ~300-500 words
    LONG = "long"        # ~500-800 words


class StoryType(str, Enum):
    """Available story types/genres."""
    REAL_HOUSEWIVES = "Real Housewives"
    NATURE_DOCUMENTARY = "Nature Documentary" 
    CHILDREN_BEDTIME = "Children's Bedtime"
    ADVENTURE = "Adventure"
    FRIENDSHIP = "Friendship"
    COMEDY = "Comedy"
    EDUCATIONAL = "Educational"


class EpisodeStatus(str, Enum):
    """Episode publication status."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ReleaseFrequency(str, Enum):
    """Release frequency options for serialized stories."""
    DAILY = "daily"
    WEEKLY = "weekly" 
    CUSTOM = "custom"


class TimeRange(BaseModel):
    """Time range for story data aggregation."""
    start: str = Field(..., description="ISO format timestamp")
    end: str = Field(..., description="ISO format timestamp")
    
    @validator('start', 'end')
    def validate_iso_format(cls, v):
        """Validate ISO timestamp format."""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            raise ValueError(f"Invalid ISO timestamp format: {v}")


class SpeciesCount(BaseModel):
    """Species count information for story context."""
    species: str = Field(..., description="Bird species name")
    count: int = Field(..., ge=0, description="Number of individuals detected")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Detection confidence")


class StoryCharacter(BaseModel):
    """Character information for story generation."""
    id: str = Field(..., description="Unique character identifier")
    species: str = Field(..., description="Bird species")
    archetype: str = Field(..., description="Personality archetype")
    name: Optional[str] = Field(None, description="Custom character name")
    appearance_count: int = Field(1, ge=1, description="Number of appearances")
    personality_notes: Optional[str] = Field(None, description="Additional personality details")


class UserPreferences(BaseModel):
    """User preferences for story generation."""
    story_type: StoryType = Field(..., description="Genre/style of story")
    attributes: List[str] = Field(default_factory=list, description="Character attributes to emphasize")
    age_group: Union[AgeGroup, str] = Field(..., description="Target age group or specific age (e.g., 'age:5')")
    include_morals: bool = Field(True, description="Whether to include life lessons")
    content_rating: Literal["G", "PG", "PG-13"] = Field("G", description="Content rating")
    
    # Notification preferences
    notify_email: bool = Field(True, description="Send email notifications for new episodes")
    notify_webpush: bool = Field(True, description="Send web push notifications for new episodes")
    email_address: Optional[str] = Field(None, description="Email address for notifications")
    
    @validator('age_group')
    def validate_age_group(cls, v):
        """Validate age group format."""
        if isinstance(v, str):
            # Handle specific age format like "age:5"
            if v.startswith("age:"):
                try:
                    age_num = int(v.split(":")[1])
                    if not 1 <= age_num <= 17:
                        raise ValueError("Age must be between 1 and 17")
                    return v
                except (IndexError, ValueError) as e:
                    raise ValueError(f"Invalid age format. Use 'age:X' where X is 1-17: {e}")
            # Handle enum values
            elif v in [age.value for age in AgeGroup]:
                return v
            else:
                raise ValueError(f"Invalid age group. Must be one of {[age.value for age in AgeGroup]} or 'age:X'")
        return v


class StoryRequest(BaseModel):
    """Complete story generation request payload."""
    user_id: str = Field(..., description="User identifier")
    time_range: TimeRange = Field(..., description="Data aggregation time window")
    species_counts: List[SpeciesCount] = Field(..., description="Species detection data")
    characters: List[StoryCharacter] = Field(..., description="Character instances for the story")
    user_prefs: UserPreferences = Field(..., description="User story preferences")
    life_lessons: List[str] = Field(default_factory=list, description="Life lessons to incorporate")
    length: StoryLength = Field(StoryLength.MEDIUM, description="Target story length")
    episodes: int = Field(1, ge=1, le=10, description="Number of episodes for serialized stories")
    custom_prompt: Optional[str] = Field(None, description="Additional custom instructions")
    
    # Serialized scheduling (optional)
    start_date: Optional[datetime] = Field(None, description="When to start releasing episodes")
    release_frequency: ReleaseFrequency = Field(ReleaseFrequency.DAILY, description="How often to release episodes")
    timezone: str = Field("UTC", description="User timezone for scheduling")
    is_serialized: bool = Field(False, description="True if episodes should be released over time")
    
    @validator('life_lessons')
    def validate_life_lessons(cls, v, values):
        """Validate life lessons are appropriate for age group."""
        if 'user_prefs' in values:
            age_group = values['user_prefs'].age_group
            if cls._is_child_age(age_group) and not v:
                # Suggest default life lessons for children if none provided
                return ["kindness", "sharing", "friendship"]
        return v
    
    @validator('episodes')
    def validate_episodes_with_length(cls, v, values):
        """Validate episode count makes sense with story length."""
        if v > 1 and 'length' in values and values['length'] == StoryLength.LONG:
            raise ValueError("Long stories should typically be single episodes. Consider medium length for multi-episode stories.")
        return v
    
    @staticmethod
    def _is_child_age(age_group: Union[AgeGroup, str]) -> bool:
        """Determine if age group represents a child."""
        if isinstance(age_group, str):
            if age_group.startswith("age:"):
                age_num = int(age_group.split(":")[1])
                return age_num <= 12
            return age_group in [AgeGroup.CHILD, AgeGroup.TODDLER, AgeGroup.PRESCHOOL, AgeGroup.SCHOOL_AGE]
        return age_group in [AgeGroup.CHILD, AgeGroup.TODDLER, AgeGroup.PRESCHOOL, AgeGroup.SCHOOL_AGE]
    
    def is_child_content(self) -> bool:
        """Check if this request is for child-appropriate content."""
        return self._is_child_age(self.user_prefs.age_group)
    
    def get_target_age(self) -> Optional[int]:
        """Extract specific age if provided."""
        age_group = self.user_prefs.age_group
        if isinstance(age_group, str) and age_group.startswith("age:"):
            return int(age_group.split(":")[1])
        return None


class StoryResponse(BaseModel):
    """Response from story generation."""
    episode_text: str = Field(..., description="Generated story text")
    tokens: int = Field(..., ge=0, description="Token count used")
    generation_time: float = Field(..., ge=0, description="Generation time in seconds")
    content_warnings: List[str] = Field(default_factory=list, description="Any content warnings")
    safety_score: float = Field(1.0, ge=0.0, le=1.0, description="Content safety score")


class Episode(BaseModel):
    """Database model for story episodes."""
    id: Optional[int] = Field(None, description="Episode ID")
    story_id: str = Field(..., description="Parent story identifier")
    episode_index: int = Field(..., ge=1, description="Episode number in series")
    title: Optional[str] = Field(None, description="Episode title")
    text: str = Field(..., description="Episode content")
    summary: Optional[str] = Field(None, description="Brief episode summary")
    published_at: Optional[datetime] = Field(None, description="Publication timestamp")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    status: EpisodeStatus = Field(EpisodeStatus.DRAFT, description="Publication status")
    word_count: int = Field(0, ge=0, description="Word count of episode text")
    tokens_used: int = Field(0, ge=0, description="Tokens used in generation")
    content_rating: str = Field("G", description="Content rating")
    
    @validator('text')
    def validate_text_content(cls, v):
        """Basic content validation."""
        if len(v.strip()) < 10:
            raise ValueError("Episode text must be at least 10 characters")
        return v.strip()
    
    @validator('word_count', always=True)
    def calculate_word_count(cls, v, values):
        """Auto-calculate word count if not provided."""
        if 'text' in values and (v == 0 or v is None):
            return len(values['text'].split())
        return v


class StoryMetadata(BaseModel):
    """Metadata for generated stories."""
    story_id: str = Field(..., description="Unique story identifier")
    user_id: str = Field(..., description="User who requested the story")
    title: str = Field(..., description="Story title")
    description: Optional[str] = Field(None, description="Story description")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_episodes: int = Field(1, ge=1, description="Total planned episodes")
    completed_episodes: int = Field(0, ge=0, description="Episodes generated so far")
    story_type: StoryType = Field(..., description="Story genre/type")
    age_rating: str = Field("G", description="Age rating")
    characters_featured: List[str] = Field(default_factory=list, description="Character IDs featured")
    species_featured: List[str] = Field(default_factory=list, description="Species featured")
    tags: List[str] = Field(default_factory=list, description="Story tags")
    
    @validator('completed_episodes')
    def validate_episode_completion(cls, v, values):
        """Ensure completed episodes doesn't exceed total."""
        if 'total_episodes' in values and v > values['total_episodes']:
            raise ValueError("Completed episodes cannot exceed total episodes")
        return v


class ContentFilter(BaseModel):
    """Content filtering configuration."""
    enable_profanity_filter: bool = Field(True, description="Enable profanity filtering")
    enable_violence_filter: bool = Field(True, description="Filter violent content") 
    enable_moderation_api: bool = Field(False, description="Use external moderation API")
    custom_blocked_words: List[str] = Field(default_factory=list, description="Custom words to filter")
    safety_threshold: float = Field(0.8, ge=0.0, le=1.0, description="Minimum safety score required")


class PromptTemplate(BaseModel):
    """Template for prompt generation."""
    name: str = Field(..., description="Template identifier")
    age_group: Union[AgeGroup, str] = Field(..., description="Target age group")
    story_type: StoryType = Field(..., description="Story genre")
    system_message: str = Field(..., description="System instruction for LLM")
    user_template: str = Field(..., description="User prompt template with placeholders")
    example_stories: List[str] = Field(default_factory=list, description="Few-shot examples")
    safety_instructions: List[str] = Field(default_factory=list, description="Safety guidelines")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Generation constraints")


# Validation utilities
def validate_story_request(request: Dict[str, Any]) -> StoryRequest:
    """Validate and parse story request with comprehensive error handling."""
    try:
        return StoryRequest.parse_obj(request)
    except Exception as e:
        raise ValueError(f"Invalid story request: {e}")


class StoryScheduleRequest(BaseModel):
    """Request to schedule or update story serialization."""
    story_id: str = Field(..., description="Story identifier")
    start_date: datetime = Field(..., description="When to start releasing episodes")
    release_frequency: ReleaseFrequency = Field(ReleaseFrequency.DAILY, description="Release frequency")
    timezone: str = Field("UTC", description="User timezone")
    
    @validator('start_date')
    def validate_start_date(cls, v):
        """Ensure start date is in the future."""
        if v <= datetime.now(timezone.utc):
            raise ValueError("Start date must be in the future")
        return v


class ScheduleStatus(BaseModel):
    """Current scheduling status of a story."""
    story_id: str = Field(..., description="Story identifier")
    is_serialized: bool = Field(..., description="Whether story is serialized")
    total_episodes: int = Field(..., description="Total planned episodes")
    published_episodes: int = Field(..., description="Episodes already published")
    next_release_at: Optional[datetime] = Field(None, description="Next scheduled release")
    release_frequency: ReleaseFrequency = Field(..., description="Release frequency")
    timezone: str = Field(..., description="User timezone")


class NotificationType(str, Enum):
    """Notification delivery types."""
    EMAIL = "email"
    WEBPUSH = "webpush"
    SMS = "sms"  # Future enhancement


class NotificationStatus(str, Enum):
    """Notification delivery status."""
    PENDING = "pending"
    SENT = "sent" 
    FAILED = "failed"
    RETRYING = "retrying"


class PushSubscription(BaseModel):
    """Web push subscription data."""
    user_id: str = Field(..., description="User identifier")
    endpoint: str = Field(..., description="Push service endpoint URL")
    p256dh_key: str = Field(..., description="Public key for encryption")
    auth_key: str = Field(..., description="Authentication secret")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Subscription creation time")


class NotificationPreferences(BaseModel):
    """User notification preferences."""
    user_id: str = Field(..., description="User identifier") 
    email_notifications: bool = Field(True, description="Enable email notifications")
    webpush_notifications: bool = Field(True, description="Enable web push notifications")
    email_address: Optional[str] = Field(None, description="Email address for notifications")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Preference creation time")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last preference update")


class NotificationRequest(BaseModel):
    """Request to send a notification."""
    user_id: str = Field(..., description="Target user identifier")
    story_id: str = Field(..., description="Story identifier")
    episode_index: int = Field(..., description="Episode number") 
    notification_type: NotificationType = Field(..., description="Type of notification to send")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    link_url: Optional[str] = Field(None, description="Optional link for notification")


class NotificationLog(BaseModel):
    """Log entry for notification attempts."""
    id: Optional[int] = Field(None, description="Log entry ID")
    user_id: str = Field(..., description="Target user")
    story_id: str = Field(..., description="Related story") 
    episode_index: int = Field(..., description="Episode number")
    notification_type: NotificationType = Field(..., description="Notification channel used")
    status: NotificationStatus = Field(NotificationStatus.PENDING, description="Delivery status")
    attempts: int = Field(1, description="Number of delivery attempts")
    error_message: Optional[str] = Field(None, description="Error details if failed")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Initial attempt time")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last attempt time")
    sent_at: Optional[datetime] = Field(None, description="Successful delivery time")


def sanitize_content(text: str, content_filter: ContentFilter) -> str:
    """Basic content sanitization."""
    if content_filter.enable_profanity_filter:
        # Basic profanity replacement (would be expanded with proper library)
        blocked_words = content_filter.custom_blocked_words + [
            # Basic profanity list - would use proper library in production
            "damn", "hell", "crap"
        ]
        for word in blocked_words:
            text = re.sub(rf'\b{re.escape(word)}\b', '*' * len(word), text, flags=re.IGNORECASE)
    
    return text.strip()