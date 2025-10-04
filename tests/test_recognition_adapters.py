"""
Unit tests for recognition adapters.

Tests the adapter contract for single/multi-count cases and confidence thresholds.
"""
import pytest
from typing import List
import tempfile
import os
from pathlib import Path

# Import test targets
from recognition.shared.schemas import (
    Detection, Character, RecognitionEvent, BoundingBox,
    generate_character_id, create_characters_from_detection,
    apply_confidence_threshold
)


class TestSchemas:
    """Test the shared schema models."""
    
    def test_detection_model_validation(self):
        """Test Detection model validation."""
        # Valid detection
        detection = Detection(
            species="Northern Cardinal",
            count=2,
            confidence=0.85
        )
        assert detection.species == "Northern Cardinal"
        assert detection.count == 2
        assert detection.confidence == 0.85
        assert detection.low_confidence is False
        assert detection.bbox is None
    
    def test_detection_with_bbox(self):
        """Test Detection with bounding box."""
        bbox = BoundingBox(x=0.1, y=0.2, width=0.3, height=0.4)
        detection = Detection(
            species="Blue Jay",
            count=1,
            confidence=0.92,
            bbox=bbox
        )
        assert detection.bbox.x == 0.1
        assert detection.bbox.y == 0.2
        assert detection.bbox.width == 0.3
        assert detection.bbox.height == 0.4
    
    def test_detection_validation_errors(self):
        """Test Detection validation errors."""
        # Invalid confidence (too high)
        with pytest.raises(ValueError):
            Detection(species="Test", confidence=1.5, count=1)
        
        # Invalid confidence (negative)
        with pytest.raises(ValueError):
            Detection(species="Test", confidence=-0.1, count=1)
        
        # Invalid count (zero)
        with pytest.raises(ValueError):
            Detection(species="Test", confidence=0.8, count=0)


class TestCharacterGeneration:
    """Test character generation logic."""
    
    def test_generate_character_id(self):
        """Test character ID generation."""
        # Normal species name
        char_id = generate_character_id("Northern Cardinal", 1)
        assert char_id == "northern_cardinal_1"
        
        # Species with special characters
        char_id = generate_character_id("Red-winged Blackbird", 2)
        assert char_id == "redwinged_blackbird_2"
        
        # Multiple spaces
        char_id = generate_character_id("American   Robin", 3)
        assert char_id == "american_robin_3"
    
    def test_create_characters_single_count(self):
        """Test character creation for single count detection."""
        detection = Detection(species="Blue Jay", count=1, confidence=0.85)
        characters = create_characters_from_detection(detection)
        
        # Single count should return empty list (no character instances needed)
        assert len(characters) == 0
    
    def test_create_characters_multi_count(self):
        """Test character creation for multi-count detection."""
        detection = Detection(species="Northern Cardinal", count=3, confidence=0.90)
        characters = create_characters_from_detection(detection)
        
        # Should create 3 character instances
        assert len(characters) == 3
        
        # Verify character properties
        expected_ids = ["northern_cardinal_1", "northern_cardinal_2", "northern_cardinal_3"]
        actual_ids = [char.id for char in characters]
        assert actual_ids == expected_ids
        
        # All should have same species
        for char in characters:
            assert char.species == "Northern Cardinal"
    
    def test_create_characters_edge_cases(self):
        """Test character creation edge cases."""
        # Count of 2 (minimum for character generation)
        detection = Detection(species="House Sparrow", count=2, confidence=0.75)
        characters = create_characters_from_detection(detection)
        assert len(characters) == 2
        assert characters[0].id == "house_sparrow_1"
        assert characters[1].id == "house_sparrow_2"


class TestConfidenceThreshold:
    """Test confidence threshold handling."""
    
    def test_apply_confidence_threshold_high_confidence(self):
        """Test with high confidence detection."""
        detection = Detection(species="American Robin", count=1, confidence=0.85)
        result = apply_confidence_threshold(detection, min_confidence=0.6)
        
        assert result.low_confidence is False
        assert result.confidence == 0.85
    
    def test_apply_confidence_threshold_low_confidence(self):
        """Test with low confidence detection."""
        detection = Detection(species="Unidentified", count=1, confidence=0.45)
        result = apply_confidence_threshold(detection, min_confidence=0.6)
        
        assert result.low_confidence is True
        assert result.confidence == 0.45
    
    def test_apply_confidence_threshold_exact_threshold(self):
        """Test with confidence exactly at threshold."""
        detection = Detection(species="House Finch", count=1, confidence=0.6)
        result = apply_confidence_threshold(detection, min_confidence=0.6)
        
        # At threshold should be considered high confidence
        assert result.low_confidence is False
        assert result.confidence == 0.6


class TestRecognitionEvent:
    """Test the unified recognition event."""
    
    def test_recognition_event_audio(self):
        """Test audio recognition event."""
        detections = [
            Detection(species="Northern Cardinal", count=2, confidence=0.90),
            Detection(species="Blue Jay", count=1, confidence=0.75)
        ]
        characters = [
            Character(id="northern_cardinal_1", species="Northern Cardinal"),
            Character(id="northern_cardinal_2", species="Northern Cardinal")
        ]
        
        event = RecognitionEvent(
            timestamp="2025-10-04T12:00:00Z",
            source="audio",
            detections=detections,
            characters=characters,
            snapshot_url="http://example.com/audio.wav"
        )
        
        assert event.source == "audio"
        assert len(event.detections) == 2
        assert len(event.characters) == 2
        assert event.snapshot_url == "http://example.com/audio.wav"
    
    def test_recognition_event_image_with_bbox(self):
        """Test image recognition event with bounding boxes."""
        bbox = BoundingBox(x=0.1, y=0.2, width=0.3, height=0.4)
        detections = [
            Detection(
                species="Red-winged Blackbird", 
                count=1, 
                confidence=0.88,
                bbox=bbox
            )
        ]
        
        event = RecognitionEvent(
            timestamp="2025-10-04T12:00:00Z",
            source="image",
            detections=detections,
            characters=[],  # Single count, no characters
            snapshot_url="http://example.com/image.jpg"
        )
        
        assert event.source == "image"
        assert len(event.detections) == 1
        assert event.detections[0].bbox is not None
        assert len(event.characters) == 0


class TestAdapterContractCompliance:
    """Test adapter contract compliance scenarios."""
    
    def test_single_detection_scenario(self):
        """Test single species, single count detection."""
        detection = Detection(
            species="American Robin",
            count=1,
            confidence=0.85
        )
        
        # Apply threshold
        detection = apply_confidence_threshold(detection, 0.6)
        
        # Generate characters
        characters = create_characters_from_detection(detection)
        
        # Verify contract compliance
        assert detection.low_confidence is False  # High confidence
        assert len(characters) == 0  # Single count = no character instances
    
    def test_multi_count_scenario(self):
        """Test single species, multiple count detection."""
        detection = Detection(
            species="Northern Cardinal",
            count=3,
            confidence=0.92
        )
        
        # Apply threshold
        detection = apply_confidence_threshold(detection, 0.6)
        
        # Generate characters
        characters = create_characters_from_detection(detection)
        
        # Verify contract compliance
        assert detection.low_confidence is False  # High confidence
        assert len(characters) == 3  # Multi-count = character instances
        assert all(char.species == "Northern Cardinal" for char in characters)
        assert characters[0].id == "northern_cardinal_1"
        assert characters[1].id == "northern_cardinal_2"
        assert characters[2].id == "northern_cardinal_3"
    
    def test_low_confidence_scenario(self):
        """Test low confidence detection."""
        detection = Detection(
            species="Unidentified Bird",
            count=1,
            confidence=0.45
        )
        
        # Apply threshold
        detection = apply_confidence_threshold(detection, 0.6)
        
        # Generate characters
        characters = create_characters_from_detection(detection)
        
        # Verify contract compliance
        assert detection.low_confidence is True  # Below threshold
        assert len(characters) == 0  # Single count = no character instances
    
    def test_multi_species_scenario(self):
        """Test multiple species detection."""
        detections = [
            Detection(species="Northern Cardinal", count=2, confidence=0.90),
            Detection(species="Blue Jay", count=1, confidence=0.85),
            Detection(species="House Sparrow", count=4, confidence=0.55)  # Low confidence
        ]
        
        # Process all detections
        processed_detections = []
        all_characters = []
        
        for detection in detections:
            # Apply threshold
            processed_detection = apply_confidence_threshold(detection, 0.6)
            processed_detections.append(processed_detection)
            
            # Generate characters
            characters = create_characters_from_detection(processed_detection)
            all_characters.extend(characters)
        
        # Verify contract compliance
        assert len(processed_detections) == 3
        
        # Northern Cardinal: high confidence, multi-count
        assert processed_detections[0].low_confidence is False
        cardinal_chars = [c for c in all_characters if c.species == "Northern Cardinal"]
        assert len(cardinal_chars) == 2
        
        # Blue Jay: high confidence, single count
        assert processed_detections[1].low_confidence is False
        jay_chars = [c for c in all_characters if c.species == "Blue Jay"]
        assert len(jay_chars) == 0  # Single count
        
        # House Sparrow: low confidence, multi-count
        assert processed_detections[2].low_confidence is True
        sparrow_chars = [c for c in all_characters if c.species == "House Sparrow"]
        assert len(sparrow_chars) == 4  # Still generate characters despite low confidence
        
        # Total characters: 2 (cardinal) + 0 (jay) + 4 (sparrow) = 6
        assert len(all_characters) == 6


# Test fixtures
@pytest.fixture
def temp_audio_file():
    """Create a temporary audio file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        f.write(b'fake audio data')
        temp_path = Path(f.name)
    
    yield temp_path
    
    # Cleanup
    if temp_path.exists():
        os.unlink(temp_path)


@pytest.fixture
def temp_image_file():
    """Create a temporary image file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
        f.write(b'fake image data')
        temp_path = Path(f.name)
    
    yield temp_path
    
    # Cleanup
    if temp_path.exists():
        os.unlink(temp_path)