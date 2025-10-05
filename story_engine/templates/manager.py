"""
Template Manager for Story Generation.

Handles loading, parsing, and managing prompt templates with age-appropriate
content selection and placeholder replacement.
"""
import os
import yaml
from typing import Dict, Any, Optional, List
from pathlib import Path
import re
from string import Template

from ..models import StoryRequest, AgeGroup, StoryType


class TemplateManager:
    """Manages prompt templates and content generation."""
    
    def __init__(self, templates_dir: Optional[str] = None):
        """Initialize template manager with template directory."""
        if templates_dir is None:
            templates_dir = Path(__file__).parent
        
        self.templates_dir = Path(templates_dir)
        self.templates: Dict[str, Any] = {}
        self.age_instructions: Dict[str, str] = {}
        self.life_lessons: Dict[str, str] = {}
        self.safety_guidelines: Dict[str, List[str]] = {}
        
        self._load_templates()
    
    def _load_templates(self):
        """Load all template files from the templates directory."""
        template_file = self.templates_dir / "prompt_templates.yaml"
        
        if not template_file.exists():
            raise FileNotFoundError(f"Template file not found: {template_file}")
        
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            self.templates = data.get('templates', {})
            self.age_instructions = data.get('age_instructions', {})
            self.life_lessons = data.get('life_lessons', {})
            self.safety_guidelines = data.get('safety_guidelines', {})
            
            print(f"Loaded {len(self.templates)} templates from {template_file}")
            
        except Exception as e:
            raise RuntimeError(f"Failed to load templates: {e}")
    
    def get_template(self, story_request: StoryRequest) -> Dict[str, Any]:
        """
        Select and return the appropriate template for a story request.
        
        Args:
            story_request: The story generation request
            
        Returns:
            Template dictionary with all necessary fields
        """
        # Determine template key based on age group and story type
        template_key = self._select_template_key(
            story_request.user_prefs.age_group,
            story_request.user_prefs.story_type
        )
        
        if template_key not in self.templates:
            # Fall back to a default template
            template_key = self._get_fallback_template(story_request.is_child_content())
        
        template = self.templates[template_key].copy()
        
        # Add computed fields
        template['word_count'] = self._get_target_word_count(story_request.length)
        template['max_words'] = template['word_count']
        
        return template
    
    def _select_template_key(self, age_group: str, story_type: StoryType) -> str:
        """Select the best template key based on age group and story type."""
        # Normalize age group
        if isinstance(age_group, str) and age_group.startswith("age:"):
            age_num = int(age_group.split(":")[1])
            if age_num <= 8:
                age_category = "child"
            elif age_num <= 12:
                age_category = "school_age"
            elif age_num <= 17:
                age_category = "teen"
            else:
                age_category = "adult"
        else:
            age_category = age_group
        
        # Map to template keys
        template_mapping = {
            ("child", "Friendship"): "child_friendship",
            ("child", "Children's Bedtime"): "child_friendship",
            ("child", "Educational"): "educational_nature",
            ("school_age", "Educational"): "educational_nature",
            ("school_age", "Nature Documentary"): "educational_nature",
            ("adult", "Real Housewives"): "adult_drama", 
            ("adult", "Comedy"): "adult_drama",
            ("teen", "Adventure"): "adult_drama"
        }
        
        key = (age_category, story_type.value if hasattr(story_type, 'value') else str(story_type))
        return template_mapping.get(key, self._get_fallback_template(age_category in ["child", "toddler", "preschool"]))
    
    def _get_fallback_template(self, is_child: bool) -> str:
        """Get fallback template based on whether content is for children."""
        return "child_friendship" if is_child else "adult_drama"
    
    def _get_target_word_count(self, length: str) -> int:
        """Get target word count based on story length."""
        word_counts = {
            "short": 150,
            "medium": 300, 
            "long": 500
        }
        return word_counts.get(length, 300)
    
    def fill_template(self, template: Dict[str, Any], story_request: StoryRequest) -> Dict[str, str]:
        """
        Fill template placeholders with story request data.
        
        Args:
            template: Template dictionary
            story_request: Story generation request
            
        Returns:
            Dictionary with filled system_message and user_prompt
        """
        # Prepare replacement data
        replacements = self._prepare_replacements(template, story_request)
        
        # Fill system message
        system_message = self._fill_placeholders(template['system_message'], replacements)
        
        # Fill user template  
        user_prompt = self._fill_placeholders(template['user_template'], replacements)
        
        return {
            'system_message': system_message,
            'user_prompt': user_prompt,
            'template_name': template['name'],
            'constraints': template.get('constraints', {}),
            'safety_instructions': template.get('safety_instructions', [])
        }
    
    def _prepare_replacements(self, template: Dict[str, Any], story_request: StoryRequest) -> Dict[str, str]:
        """Prepare all placeholder replacement values."""
        # Format characters
        characters_text = self._format_characters(story_request.characters)
        
        # Format species counts
        species_counts_text = self._format_species_counts(story_request.species_counts)
        
        # Get age instructions
        age_instructions = self._get_age_instructions(story_request.user_prefs.age_group)
        
        # Format life lessons
        life_lessons_text = self._format_life_lessons(story_request.life_lessons)
        
        # Get attributes
        attributes_text = ", ".join(story_request.user_prefs.attributes) if story_request.user_prefs.attributes else "friendly, interesting"
        
        # Get story type
        story_type = story_request.user_prefs.story_type.value if hasattr(story_request.user_prefs.story_type, 'value') else str(story_request.user_prefs.story_type)
        
        return {
            'characters': characters_text,
            'species_counts': species_counts_text,
            'age_instructions': age_instructions,
            'life_lessons': life_lessons_text,
            'attributes': attributes_text,
            'story_type': story_type,
            'length': story_request.length.value if hasattr(story_request.length, 'value') else str(story_request.length),
            'word_count': str(template.get('word_count', 300)),
            'max_words': str(template.get('max_words', 300))
        }
    
    def _format_characters(self, characters: List[Any]) -> str:
        """Format characters for template insertion."""
        if not characters:
            return "A friendly bird community at the feeder"
        
        formatted = []
        for char in characters:
            name = getattr(char, 'name', None) or f"a {char.species}"
            species = char.species
            archetype = char.archetype
            appearances = getattr(char, 'appearance_count', 1)
            
            char_desc = f"- {name} ({species}): {archetype}"
            if appearances > 1:
                char_desc += f" - seen {appearances} times"
                
            formatted.append(char_desc)
        
        return "\n".join(formatted)
    
    def _format_species_counts(self, species_counts: List[Any]) -> str:
        """Format species counts for template insertion."""
        if not species_counts:
            return "Various birds visiting the feeder"
        
        formatted = []
        for species in species_counts:
            count_text = f"{species.count} {species.species}"
            if species.count != 1:
                count_text += "s"  # Simple pluralization
            
            if hasattr(species, 'confidence') and species.confidence:
                count_text += f" (confidence: {species.confidence:.1%})"
            
            formatted.append(f"- {count_text}")
        
        return "\n".join(formatted)
    
    def _get_age_instructions(self, age_group: str) -> str:
        """Get age-specific instructions."""
        # Handle specific age format
        if isinstance(age_group, str) and age_group.startswith("age:"):
            age_num = int(age_group.split(":")[1])
            if age_num <= 4:
                key = "toddler"
            elif age_num <= 8:
                key = "child"
            elif age_num <= 12:
                key = "school_age"
            elif age_num <= 17:
                key = "teen"
            else:
                key = "adult"
        else:
            key = age_group
        
        return self.age_instructions.get(key, self.age_instructions.get("child", "Age-appropriate content"))
    
    def _format_life_lessons(self, life_lessons: List[str]) -> str:
        """Format life lessons with descriptions."""
        if not life_lessons:
            return "friendship and kindness"
        
        formatted_lessons = []
        for lesson in life_lessons:
            description = self.life_lessons.get(lesson, lesson)
            formatted_lessons.append(description)
        
        return ", ".join(formatted_lessons)
    
    def _fill_placeholders(self, text: str, replacements: Dict[str, str]) -> str:
        """Fill placeholders in text using safe string template substitution."""
        try:
            # Use string.Template for safe substitution
            template = Template(text)
            return template.safe_substitute(replacements)
        except Exception as e:
            print(f"Warning: Template substitution failed: {e}")
            return text
    
    def get_safety_guidelines(self, is_child_content: bool) -> List[str]:
        """Get applicable safety guidelines."""
        guidelines = self.safety_guidelines.get('universal', []).copy()
        
        if is_child_content:
            guidelines.extend(self.safety_guidelines.get('child_specific', []))
        else:
            guidelines.extend(self.safety_guidelines.get('adult_specific', []))
        
        return guidelines
    
    def get_example_story(self, template_name: str) -> Optional[str]:
        """Get example story for few-shot prompting."""
        template = self.templates.get(template_name, {})
        examples = template.get('example_stories', [])
        return examples[0] if examples else None
    
    def reload_templates(self):
        """Reload templates from disk (useful for development)."""
        self._load_templates()


# Global template manager instance
template_manager = TemplateManager()