"""
Integration tests for recognition services.

Tests the HTTP API endpoints and full service functionality.
"""
import pytest
import requests
import json
import tempfile
from pathlib import Path

# Test configuration
AUDIO_SERVICE_URL = "http://localhost:8002"
IMAGE_SERVICE_URL = "http://localhost:8003"


class TestAudioRecognitionAPI:
    """Test audio recognition service API."""
    
    def test_health_endpoint(self):
        """Test audio service health endpoint."""
        response = requests.get(f"{AUDIO_SERVICE_URL}/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert health_data["status"] == "healthy"
        assert health_data["service"] == "audio-recognizer"
        assert "model_loaded" in health_data
        assert "min_confidence" in health_data
    
    def test_root_endpoint(self):
        """Test audio service root endpoint."""
        response = requests.get(f"{AUDIO_SERVICE_URL}/")
        assert response.status_code == 200
        
        info = response.json()
        assert "service" in info
        assert "supported_formats" in info
        assert "max_file_size" in info
    
    def test_recognize_with_url(self):
        """Test audio recognition with URL parameter."""
        response = requests.post(
            f"{AUDIO_SERVICE_URL}/recognize",
            data={"url": "http://example.com/test.wav"}
        )
        assert response.status_code == 200
        
        event = response.json()
        assert event["source"] == "audio"
        assert "timestamp" in event
        assert "detections" in event
        assert "characters" in event
        assert event["snapshot_url"] == "http://example.com/test.wav"
    
    def test_recognize_missing_input(self):
        """Test recognition with missing input."""
        response = requests.post(f"{AUDIO_SERVICE_URL}/recognize")
        assert response.status_code == 400
        
        error = response.json()
        assert "Either file or url parameter is required" in error["detail"]
    
    def test_recognize_both_inputs(self):
        """Test recognition with both file and URL (should fail)."""
        with tempfile.NamedTemporaryFile(suffix='.wav') as temp_file:
            temp_file.write(b'fake audio data')
            temp_file.flush()
            
            with open(temp_file.name, 'rb') as f:
                response = requests.post(
                    f"{AUDIO_SERVICE_URL}/recognize",
                    files={"file": f},
                    data={"url": "http://example.com/test.wav"}
                )
        
        assert response.status_code == 400
        error = response.json()
        assert "Provide either file or url, not both" in error["detail"]


class TestImageRecognitionAPI:
    """Test image recognition service API."""
    
    def test_health_endpoint(self):
        """Test image service health endpoint."""
        response = requests.get(f"{IMAGE_SERVICE_URL}/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert health_data["status"] == "healthy"
        assert health_data["service"] == "image-recognizer"
        assert "model_loaded" in health_data
        assert "min_confidence" in health_data
    
    def test_root_endpoint(self):
        """Test image service root endpoint."""
        response = requests.get(f"{IMAGE_SERVICE_URL}/")
        assert response.status_code == 200
        
        info = response.json()
        assert "service" in info
        assert "supported_formats" in info
        assert "max_file_size" in info
    
    def test_recognize_with_url(self):
        """Test image recognition with URL parameter."""
        response = requests.post(
            f"{IMAGE_SERVICE_URL}/recognize",
            data={"url": "http://example.com/test.jpg"}
        )
        assert response.status_code == 200
        
        event = response.json()
        assert event["source"] == "image"
        assert "timestamp" in event
        assert "detections" in event
        assert "characters" in event
        assert event["snapshot_url"] == "http://example.com/test.jpg"
        
        # Image detections should have bounding boxes
        for detection in event["detections"]:
            if detection["bbox"]:  # Some detections might not have bbox
                assert "x" in detection["bbox"]
                assert "y" in detection["bbox"]
                assert "width" in detection["bbox"]
                assert "height" in detection["bbox"]


class TestRecognitionEventSchema:
    """Test the unified recognition event schema compliance."""
    
    def test_audio_event_schema(self):
        """Test audio recognition event schema compliance."""
        response = requests.post(
            f"{AUDIO_SERVICE_URL}/recognize",
            data={"url": "http://example.com/test.wav"}
        )
        assert response.status_code == 200
        
        event = response.json()
        
        # Verify required fields
        assert "timestamp" in event
        assert "source" in event
        assert "detections" in event
        assert "characters" in event
        assert event["source"] == "audio"
        
        # Verify detection schema
        for detection in event["detections"]:
            assert "species" in detection
            assert "count" in detection
            assert "confidence" in detection
            assert "low_confidence" in detection
            assert detection["count"] >= 1
            assert 0.0 <= detection["confidence"] <= 1.0
        
        # Verify character schema for multi-count detections
        multi_count_detections = [d for d in event["detections"] if d["count"] > 1]
        expected_character_count = sum(d["count"] for d in multi_count_detections)
        assert len(event["characters"]) == expected_character_count
        
        for character in event["characters"]:
            assert "id" in character
            assert "species" in character
    
    def test_image_event_schema(self):
        """Test image recognition event schema compliance."""
        response = requests.post(
            f"{IMAGE_SERVICE_URL}/recognize",
            data={"url": "http://example.com/test.jpg"}
        )
        assert response.status_code == 200
        
        event = response.json()
        
        # Verify required fields
        assert "timestamp" in event
        assert "source" in event
        assert "detections" in event
        assert "characters" in event
        assert event["source"] == "image"
        
        # Verify detection schema (images may have bounding boxes)
        for detection in event["detections"]:
            assert "species" in detection
            assert "count" in detection
            assert "confidence" in detection
            assert "low_confidence" in detection
            assert "bbox" in detection  # May be null
            
            # If bbox exists, verify structure
            if detection["bbox"]:
                bbox = detection["bbox"]
                assert "x" in bbox
                assert "y" in bbox
                assert "width" in bbox
                assert "height" in bbox
                assert 0.0 <= bbox["x"] <= 1.0
                assert 0.0 <= bbox["y"] <= 1.0
                assert 0.0 <= bbox["width"] <= 1.0
                assert 0.0 <= bbox["height"] <= 1.0


class TestConfidenceThresholds:
    """Test confidence threshold functionality."""
    
    def test_confidence_flagging(self):
        """Test that low confidence detections are properly flagged."""
        # Test audio service
        response = requests.post(
            f"{AUDIO_SERVICE_URL}/recognize",
            data={"url": "http://example.com/test.wav"}
        )
        assert response.status_code == 200
        
        event = response.json()
        
        # Check that detections have low_confidence flags
        for detection in event["detections"]:
            confidence = detection["confidence"]
            low_confidence = detection["low_confidence"]
            
            # The flag should be consistent with the threshold (default 0.6)
            expected_low_confidence = confidence < 0.6
            assert low_confidence == expected_low_confidence


# Pytest markers for different test categories
pytestmark = pytest.mark.integration