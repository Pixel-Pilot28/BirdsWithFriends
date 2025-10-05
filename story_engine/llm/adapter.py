"""
LLM Adapter for Story Generation.

Provides abstraction layer for different LLM providers with mock implementation
for testing and development. Handles prompt formatting, safety filtering,
and response processing.
"""
import time
import json
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from abc import ABC, abstractmethod

from ..models import StoryRequest, StoryResponse, ContentFilter, sanitize_content


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate(
        self, 
        system_message: str, 
        user_prompt: str, 
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """Generate story content from prompts."""
        pass


class MockLLMProvider(BaseLLMProvider):
    """Mock LLM provider for testing and development."""
    
    def __init__(self):
        self.generation_count = 0
        self.mock_stories = {
            'child': [
                """Once upon a time at the Cornell Lab feeder, there lived a cheerful Northern Cardinal named Ruby. Ruby had the brightest red feathers and loved to help other birds.

One sunny morning, Ruby noticed a new Blue Jay named Jay sitting alone on a branch. Jay looked sad and hungry.

"Hello!" chirped Ruby kindly. "Would you like to share some seeds with me?"

Jay's eyes lit up. "Really? You would share with me?"

"Of course!" said Ruby. "Sharing makes everything better. There are plenty of seeds for everyone."

Ruby showed Jay the best spots to find sunflower seeds. Soon, other birds came to join them. They all shared their seeds and became good friends.

"Thank you for teaching me about sharing," said Jay happily. "Now I want to share with others too!"

From that day on, all the birds at the feeder shared with each other. They learned that when we share, everyone is happy and no one goes hungry.

And Ruby felt warm and happy inside, knowing that sharing kindness makes the world a better place for everyone.""",
                
                """At the magical Cornell Lab feeder, three little bird friends were learning something very important about being kind to each other.

Emma the American Robin was trying to crack a big sunflower seed, but it was too hard for her small beak. She felt frustrated and ready to give up.

"I can't do it," Emma sighed sadly.

Charlie the Northern Cardinal heard her and flew over quickly. "Don't worry, Emma! I can help you. My beak is strong and good for cracking seeds."

Charlie cracked the seed and shared half with Emma. "Here you go, friend!"

Just then, Bella the Blue Jay landed nearby. "What are you two doing?"

"Charlie helped me crack my seed because I was having trouble," explained Emma happily.

"That's wonderful!" said Bella. "Being kind to friends is the most important thing. Let me help you find more seeds."

Together, the three friends helped each other all day long. Charlie cracked seeds, Emma found the juiciest berries, and Bella used her smart brain to remember where the best food was hidden.

"We make such a good team when we're kind to each other," said Emma.

"Yes," agreed Charlie. "Kindness makes everything easier and more fun!"

And all the birds at the feeder learned that when friends are kind and help each other, every day becomes a wonderful adventure."""
            ],
            'adult': [
                """The morning drama at the Cornell Lab feeder reached new heights as Scarlett, the self-proclaimed queen of the Cardinals, swept in with her usual flair for the theatrical.

"Well, well," she announced, her red feathers practically glowing with indignation, "I see the Blue Jay mafia has claimed the premium real estate again."

Jake, the notoriously clever Blue Jay, preened his crest with exaggerated nonchalance. "Oh, Scarlett darling, we prefer to think of it as strategic positioning. After all, early bird gets the worm, but the smart bird gets the sunflower seeds."

The assembled Robin sisters – Robin, Roberta, and Robyn – exchanged knowing glances. They'd been watching this territorial dispute unfold for weeks with the fascination of spectators at a tennis match.

"Perhaps," suggested Robin diplomatically, "we could establish a rotation system? You know, share the space like civilized birds?"

Scarlett's laugh was sharp as a winter wind. "Share? With birds who hoard shiny objects and terrorize the neighborhood cats? I think not."

Jake's eyes glittered with mischief. "Speaking of hoarding, didn't I see you stuffing seeds under the azalea bush yesterday? Glass houses, sweetheart."

The confrontation might have escalated further, but a sudden arrival of house finches created enough chaos for everyone to claim their preferred spots. 

As the dust settled, Roberta whispered to her sisters, "Same time tomorrow for the next episode?"

Because at the Cornell Lab feeder, the birds were beautiful, the seeds were plentiful, and the drama was absolutely delicious.""",
                
                """It was another gloriously chaotic morning at the Cornell Lab feeder, where reputations were made, broken, and remade before most humans had finished their coffee.

The scandal du jour involved Jasper, the charming but unreliable Blue Jay, and his alleged theft of Miranda the Cardinal's carefully curated seed stash. The accusation had sent ripples through the entire avian social hierarchy.

"I cannot believe the audacity," Miranda declared to her breakfast companions, a cluster of impressed chickadees. "Forty-seven premium sunflower seeds, gone! And everyone knows Jasper has sticky talons when it comes to other birds' property."

From his perch on the feeder's edge, Jasper maintained his innocence with the smooth confidence of a practiced charmer. "Miranda, darling, you wound me. Just because I appreciate quality doesn't mean I'm a thief. Perhaps you simply miscounted?"

The suggestion sent Miranda into such a state that her red feathers seemed to vibrate with fury. "Miscounted? I'll have you know I have an accounting degree from Cornell – well, I would if birds could get degrees!"

Enter Oliver, the distinguished older Robin who served as the feeder's unofficial mediator. His grey-speckled chest and wise demeanor commanded immediate respect.

"Now, now," Oliver intervened smoothly, "surely we can resolve this like the sophisticated birds we are. Jasper, perhaps a gesture of goodwill? Miranda, maybe a touch of forgiveness?"

The resolution came in the form of Jasper's offering to share his secret cache of thistle seeds – a delicacy that had Miranda practically swooning with delight.

And so another crisis was averted, another alliance formed, and another chapter written in the ongoing soap opera that was life at the Cornell Lab feeder."""
            ]
        }
    
    async def generate(
        self, 
        system_message: str, 
        user_prompt: str, 
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """Generate mock story content."""
        start_time = time.time()
        
        # Simulate processing time
        await self._simulate_processing_time()
        
        # Determine content type from prompts
        is_child_content = self._is_child_content(system_message, user_prompt)
        
        # Select appropriate mock story
        story_text = self._select_mock_story(is_child_content)
        
        # Simulate token usage
        tokens = len(story_text.split()) * 1.3  # Rough token approximation
        
        generation_time = time.time() - start_time
        self.generation_count += 1
        
        return {
            'text': story_text,
            'tokens': int(tokens),
            'generation_time': generation_time,
            'provider': 'mock',
            'model': 'mock-gpt-3.5-turbo'
        }
    
    async def _simulate_processing_time(self):
        """Simulate realistic LLM processing time."""
        import asyncio
        # Simulate 0.5-2 second processing time
        delay = 0.5 + (self.generation_count % 3) * 0.5
        await asyncio.sleep(delay)
    
    def _is_child_content(self, system_message: str, user_prompt: str) -> bool:
        """Determine if content is for children based on prompts."""
        child_indicators = [
            'child', 'children', 'kid', 'young', 'simple', 'age-appropriate',
            'life lesson', 'moral', 'bedtime', 'family-friendly'
        ]
        
        combined_text = (system_message + " " + user_prompt).lower()
        
        return any(indicator in combined_text for indicator in child_indicators)
    
    def _select_mock_story(self, is_child_content: bool) -> str:
        """Select appropriate mock story based on content type."""
        story_type = 'child' if is_child_content else 'adult'
        stories = self.mock_stories[story_type]
        
        # Rotate through available stories
        story_index = self.generation_count % len(stories)
        return stories[story_index]


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider (for production use)."""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        self.api_key = api_key
        self.model = model
        # In production, would initialize OpenAI client here
    
    async def generate(
        self, 
        system_message: str, 
        user_prompt: str, 
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """Generate story using OpenAI API."""
        # This would be implemented with actual OpenAI API calls
        # For now, fall back to mock
        mock_provider = MockLLMProvider()
        return await mock_provider.generate(system_message, user_prompt, max_tokens, temperature)


class LLMAdapter:
    """Main adapter class for story generation."""
    
    def __init__(self, provider: Optional[BaseLLMProvider] = None, content_filter: Optional[ContentFilter] = None):
        """Initialize LLM adapter with provider and content filter."""
        self.provider = provider or MockLLMProvider()
        self.content_filter = content_filter or ContentFilter()
        self.generation_stats = {
            'total_generations': 0,
            'total_tokens': 0,
            'average_generation_time': 0.0,
            'safety_violations': 0
        }
    
    async def generate_story(self, story_request: StoryRequest, filled_template: Dict[str, str]) -> StoryResponse:
        """
        Generate story from request and filled template.
        
        Args:
            story_request: Story generation request
            filled_template: Template with placeholders filled
            
        Returns:
            StoryResponse with generated content and metadata
        """
        try:
            # Extract prompts from filled template
            system_message = filled_template['system_message']
            user_prompt = filled_template['user_prompt']
            
            # Determine generation parameters
            max_tokens = self._calculate_max_tokens(story_request.length)
            temperature = self._get_temperature(story_request.user_prefs.story_type)
            
            # Generate content
            result = await self.provider.generate(
                system_message=system_message,
                user_prompt=user_prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            # Process and filter content
            story_text = result['text']
            filtered_text, warnings = self._filter_content(story_text, story_request.is_child_content())
            
            # Calculate safety score
            safety_score = self._calculate_safety_score(filtered_text, warnings)
            
            # Update statistics
            self._update_stats(result)
            
            return StoryResponse(
                episode_text=filtered_text,
                tokens=result['tokens'],
                generation_time=result['generation_time'],
                content_warnings=warnings,
                safety_score=safety_score
            )
            
        except Exception as e:
            raise RuntimeError(f"Story generation failed: {e}")
    
    def _calculate_max_tokens(self, length: str) -> int:
        """Calculate max tokens based on story length."""
        token_limits = {
            'short': 300,
            'medium': 600,
            'long': 1000
        }
        return token_limits.get(length, 600)
    
    def _get_temperature(self, story_type: str) -> float:
        """Get generation temperature based on story type."""
        temperatures = {
            'Educational': 0.3,          # More factual, less creative
            'Nature Documentary': 0.4,   # Slightly more creative
            'Children\'s Bedtime': 0.6,  # Moderate creativity
            'Friendship': 0.7,           # Good creativity
            'Real Housewives': 0.8,      # High creativity for drama
            'Comedy': 0.9                # Maximum creativity for humor
        }
        
        story_type_str = story_type.value if hasattr(story_type, 'value') else str(story_type)
        return temperatures.get(story_type_str, 0.7)
    
    def _filter_content(self, text: str, is_child_content: bool) -> tuple[str, List[str]]:
        """Filter content for safety and appropriateness."""
        warnings = []
        
        # Apply content filtering
        filtered_text = sanitize_content(text, self.content_filter)
        
        if filtered_text != text:
            warnings.append("Content was filtered for inappropriate language")
        
        # Check for child-specific issues
        if is_child_content:
            child_warnings = self._check_child_content(filtered_text)
            warnings.extend(child_warnings)
        
        # Check length constraints
        word_count = len(filtered_text.split())
        if word_count > 1000:
            warnings.append(f"Story is longer than recommended ({word_count} words)")
        
        return filtered_text, warnings
    
    def _check_child_content(self, text: str) -> List[str]:
        """Check content for child appropriateness."""
        warnings = []
        
        # Check for potentially scary words
        scary_words = ['death', 'die', 'kill', 'blood', 'scary', 'frightening', 'terror']
        text_lower = text.lower()
        
        found_scary = [word for word in scary_words if word in text_lower]
        if found_scary:
            warnings.append(f"Content may be too scary for children: {', '.join(found_scary)}")
        
        # Check sentence length for readability
        sentences = re.split(r'[.!?]+', text)
        long_sentences = [s for s in sentences if len(s.split()) > 20]
        if long_sentences:
            warnings.append("Some sentences may be too long for young readers")
        
        return warnings
    
    def _calculate_safety_score(self, text: str, warnings: List[str]) -> float:
        """Calculate content safety score."""
        base_score = 1.0
        
        # Deduct points for warnings
        score_deduction = len(warnings) * 0.1
        
        # Additional checks
        profanity_check = self._check_profanity(text)
        if profanity_check:
            score_deduction += 0.3
        
        return max(0.0, base_score - score_deduction)
    
    def _check_profanity(self, text: str) -> bool:
        """Basic profanity check (would use proper library in production)."""
        # Basic profanity list - in production would use proper filtering library
        basic_profanity = ['damn', 'hell', 'crap', 'stupid', 'idiot']
        text_lower = text.lower()
        
        return any(word in text_lower for word in basic_profanity)
    
    def _update_stats(self, result: Dict[str, Any]):
        """Update generation statistics."""
        self.generation_stats['total_generations'] += 1
        self.generation_stats['total_tokens'] += result['tokens']
        
        # Update average generation time
        old_avg = self.generation_stats['average_generation_time']
        count = self.generation_stats['total_generations']
        new_time = result['generation_time']
        
        self.generation_stats['average_generation_time'] = (old_avg * (count - 1) + new_time) / count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get generation statistics."""
        return self.generation_stats.copy()
    
    async def validate_content(self, text: str, is_child_content: bool = False) -> Dict[str, Any]:
        """Validate content against safety guidelines."""
        warnings = []
        
        # Basic validation
        if len(text.strip()) < 50:
            warnings.append("Content is too short")
        
        if len(text) > 5000:
            warnings.append("Content exceeds maximum length")
        
        # Child content validation
        if is_child_content:
            child_warnings = self._check_child_content(text)
            warnings.extend(child_warnings)
        
        # Calculate safety score
        safety_score = self._calculate_safety_score(text, warnings)
        
        return {
            'is_safe': safety_score >= self.content_filter.safety_threshold,
            'safety_score': safety_score,
            'warnings': warnings,
            'word_count': len(text.split())
        }


# Global LLM adapter instance
llm_adapter = LLMAdapter()