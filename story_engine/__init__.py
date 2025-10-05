"""
Birds with Friends - Story Engine Module

Generates age-appropriate bird stories from aggregated recognition data.
Includes comprehensive safety features, content filtering, and episode management.
"""

from .models import (
    StoryRequest,
    StoryResponse, 
    Episode,
    StoryMetadata,
    AgeGroup,
    StoryType,
    StoryLength,
    EpisodeStatus
)

from .llm.adapter import LLMAdapter, llm_adapter
from .templates.manager import TemplateManager, template_manager

__version__ = "1.0.0"
__author__ = "Birds with Friends Team"

# Main exports
__all__ = [
    "StoryRequest",
    "StoryResponse", 
    "Episode",
    "StoryMetadata",
    "AgeGroup",
    "StoryType", 
    "StoryLength",
    "EpisodeStatus",
    "LLMAdapter",
    "llm_adapter",
    "TemplateManager", 
    "template_manager"
]