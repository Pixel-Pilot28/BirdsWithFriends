"""
Test suite for Backend API endpoints (Feature 7).

Tests all REST endpoints with OpenAPI documentation compliance.
"""
import pytest
import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from httpx import AsyncClient
import httpx

from story_engine.service import app
from story_engine.database import get_db
from story_engine.models import NotificationPreferencesDB


# Test client for story engine service
client = TestClient(app)


class TestIngestEndpoints:
    """Test ingest-related endpoints."""
    
    @patch('httpx.AsyncClient')
    def test_trigger_sample_capture_success(self, mock_client):
        """Test successful sample capture trigger."""
        # Mock successful response from ingest service
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "sample_id": "test-123",
            "audio_file": "/tmp/audio_123.wav",
            "image_file": "/tmp/image_123.jpg"
        }
        
        # Setup async context manager
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_context
        mock_context.post.return_value = mock_response
        mock_client.return_value = mock_context
        
        response = client.post("/ingest/sample")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "sample_id" in data
    
    @patch('httpx.AsyncClient')
    def test_trigger_sample_with_params(self, mock_client):
        """Test sample capture with custom parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "sample_id": "test-456"}
        
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_context
        mock_context.post.return_value = mock_response
        mock_client.return_value = mock_context
        
        payload = {
            "source_url": "rtsp://example.com/stream",
            "duration": 10
        }
        
        response = client.post("/ingest/sample", json=payload)
        
        assert response.status_code == 200
        # Verify params were passed correctly
        mock_context.post.assert_called_once()
        args, kwargs = mock_context.post.call_args
        assert "params" in kwargs
        assert kwargs["params"]["source_url"] == "rtsp://example.com/stream"
        assert kwargs["params"]["duration"] == 10
    
    @patch('httpx.AsyncClient')
    def test_sample_capture_service_unavailable(self, mock_client):
        """Test handling when ingest service is unavailable."""
        mock_client.side_effect = httpx.RequestError("Connection failed")
        
        response = client.post("/ingest/sample")
        
        assert response.status_code == 503
        assert "unavailable" in response.json()["detail"]
    
    @patch('httpx.AsyncClient') 
    def test_sample_capture_service_error(self, mock_client):
        """Test handling when ingest service returns error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_context
        mock_context.post.return_value = mock_response
        mock_client.return_value = mock_context
        
        response = client.post("/ingest/sample")
        
        assert response.status_code == 500
        assert "Ingest service error" in response.json()["detail"]


class TestRecognitionEndpoints:
    """Test recognition event endpoints."""
    
    @patch('httpx.AsyncClient')
    def test_receive_recognition_event_success(self, mock_client):
        """Test successful recognition event processing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "event_id": "evt-123",
            "characters": ["char-1", "char-2"]
        }
        
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_context
        mock_context.post.return_value = mock_response
        mock_client.return_value = mock_context
        
        event_data = {
            "species": "Northern Cardinal",
            "confidence": 0.95,
            "timestamp": "2024-01-15T10:30:00Z",
            "source_type": "audio",
            "metadata": {"frequency": "3.5kHz"}
        }
        
        response = client.post("/recognize", json=event_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "event_id" in data
        assert "characters_updated" in data
    
    @patch('httpx.AsyncClient')
    def test_recognition_event_validation(self, mock_client):
        """Test recognition event data validation."""
        invalid_event = {
            "species": "Cardinal",
            "confidence": 1.5,  # Invalid: > 1.0
            "timestamp": "invalid-date",
            "source_type": "audio"
        }
        
        response = client.post("/recognize", json=invalid_event)
        
        assert response.status_code == 422  # Validation error
    
    @patch('httpx.AsyncClient')
    def test_recognition_aggregator_unavailable(self, mock_client):
        """Test handling when aggregator service is unavailable."""
        mock_client.side_effect = httpx.RequestError("Connection failed")
        
        event_data = {
            "species": "Blue Jay",
            "confidence": 0.8,
            "timestamp": "2024-01-15T10:30:00Z",
            "source_type": "image"
        }
        
        response = client.post("/recognize", json=event_data)
        
        assert response.status_code == 503
        assert "Aggregator service unavailable" in response.json()["detail"]


class TestAggregatorEndpoints:
    """Test aggregator summary endpoints."""
    
    @patch('httpx.AsyncClient')
    def test_get_aggregation_summary_success(self, mock_client):
        """Test successful aggregation summary retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "characters": [
                {
                    "id": "char-1",
                    "species": "Cardinal",
                    "archetype": "Leader",
                    "appearance_count": 5
                }
            ],
            "species": ["Cardinal", "Blue Jay"],
            "recent_activity": [],
            "timeframe": {
                "start": "2024-01-15T10:15:00Z",
                "end": "2024-01-15T10:30:00Z",
                "window_minutes": "15"
            }
        }
        
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_context
        mock_context.get.return_value = mock_response
        mock_client.return_value = mock_context
        
        response = client.get("/aggregator/summary?window_minutes=15")
        
        assert response.status_code == 200
        data = response.json()
        assert "characters" in data
        assert "species" in data
        assert "timeframe" in data
    
    @patch('httpx.AsyncClient')
    def test_aggregation_summary_custom_window(self, mock_client):
        """Test aggregation summary with custom window."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"characters": [], "species": []}
        
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_context  
        mock_context.get.return_value = mock_response
        mock_client.return_value = mock_context
        
        response = client.get("/aggregator/summary?window_minutes=30")
        
        assert response.status_code == 200
        # Verify correct window was passed
        mock_context.get.assert_called_once()
        args, kwargs = mock_context.get.call_args
        assert "window_minutes=30" in args[0]
    
    def test_aggregation_summary_invalid_window(self):
        """Test aggregation summary with invalid window parameter."""
        response = client.get("/aggregator/summary?window_minutes=0")
        
        assert response.status_code == 422  # Validation error


class TestCharacterEndpoints:
    """Test character management endpoints."""
    
    @patch('httpx.AsyncClient')
    def test_list_characters_success(self, mock_client):
        """Test successful character listing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": "char-1",
                "species": "Cardinal",
                "archetype": "Leader",
                "appearance_count": 5,
                "name": None
            },
            {
                "id": "char-2", 
                "species": "Blue Jay",
                "archetype": "Scout",
                "appearance_count": 3,
                "name": "Jasper"
            }
        ]
        
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_context
        mock_context.get.return_value = mock_response
        mock_client.return_value = mock_context
        
        response = client.get("/characters")
        
        assert response.status_code == 200
        characters = response.json()
        assert len(characters) == 2
        assert characters[0]["species"] == "Cardinal"
        assert characters[1]["name"] == "Jasper"
    
    @patch('httpx.AsyncClient')
    def test_list_characters_with_filters(self, mock_client):
        """Test character listing with filters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_context
        mock_context.get.return_value = mock_response
        mock_client.return_value = mock_context
        
        response = client.get("/characters?user_id=user123&species=Cardinal&active_only=true&limit=10")
        
        assert response.status_code == 200
        # Verify filters were passed
        mock_context.get.assert_called_once()
        args, kwargs = mock_context.get.call_args
        params = kwargs["params"]
        assert params["user_id"] == "user123"
        assert params["species"] == "Cardinal"
        assert params["active_only"] is True
        assert params["limit"] == 10
    
    @patch('httpx.AsyncClient')
    def test_update_character_success(self, mock_client):
        """Test successful character update."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "char-1",
            "species": "Cardinal", 
            "archetype": "Wise Elder",
            "name": "Carla",
            "updated_at": "2024-01-15T10:30:00Z"
        }
        
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_context
        mock_context.patch.return_value = mock_response
        mock_client.return_value = mock_context
        
        update_data = {
            "archetype": "Wise Elder",
            "name": "Carla"
        }
        
        response = client.patch("/characters/char-1", json=update_data)
        
        assert response.status_code == 200
        character = response.json()
        assert character["archetype"] == "Wise Elder"
        assert character["name"] == "Carla"
    
    def test_update_character_no_data(self):
        """Test character update with no update data."""
        response = client.patch("/characters/char-1", json={})
        
        assert response.status_code == 400
        assert "No updates provided" in response.json()["detail"]
    
    @patch('httpx.AsyncClient')
    def test_character_service_unavailable(self, mock_client):
        """Test handling when aggregator service is unavailable."""
        mock_client.side_effect = httpx.RequestError("Connection failed")
        
        response = client.get("/characters")
        
        assert response.status_code == 503
        assert "unavailable" in response.json()["detail"]


class TestUserEndpoints:
    """Test user management endpoints."""
    
    def test_create_user_success(self):
        """Test successful user creation."""
        with patch.object(app.dependency_overrides, 'clear'), \
             patch('story_engine.service.get_db') as mock_db:
            
            # Mock database
            mock_session = Mock()
            mock_session.query.return_value.filter.return_value.first.return_value = None
            mock_db.return_value = mock_session
            
            user_data = {
                "username": "testuser",
                "email": "test@example.com",
                "preferences": {
                    "email_notifications": True,
                    "webpush_notifications": False
                }
            }
            
            response = client.post("/users", json=user_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["username"] == "testuser"
            assert data["email"] == "test@example.com"
            assert "created_at" in data
    
    def test_create_user_duplicate_username(self):
        """Test user creation with existing username."""
        with patch.object(app.dependency_overrides, 'clear'), \
             patch('story_engine.service.get_db') as mock_db:
            
            # Mock existing user
            existing_user = Mock()
            mock_session = Mock()
            mock_session.query.return_value.filter.return_value.first.return_value = existing_user
            mock_db.return_value = mock_session
            
            user_data = {
                "username": "existinguser",
                "email": "existing@example.com"
            }
            
            response = client.post("/users", json=user_data)
            
            assert response.status_code == 400
            assert "already exists" in response.json()["detail"]
    
    def test_get_user_success(self):
        """Test successful user retrieval."""
        with patch.object(app.dependency_overrides, 'clear'), \
             patch('story_engine.service.get_db') as mock_db:
            
            # Mock user data
            mock_user = Mock()
            mock_user.user_id = "testuser"
            mock_user.email_address = "test@example.com"
            mock_user.email_notifications = True
            mock_user.webpush_notifications = False
            mock_user.created_at = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
            mock_user.updated_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
            
            mock_session = Mock()
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user
            mock_db.return_value = mock_session
            
            response = client.get("/users/testuser")
            
            assert response.status_code == 200
            data = response.json()
            assert data["username"] == "testuser"
            assert data["email"] == "test@example.com"
            assert data["preferences"]["email_notifications"] is True
    
    def test_get_user_not_found(self):
        """Test user retrieval with non-existent user."""
        with patch.object(app.dependency_overrides, 'clear'), \
             patch('story_engine.service.get_db') as mock_db:
            
            mock_session = Mock()
            mock_session.query.return_value.filter.return_value.first.return_value = None
            mock_db.return_value = mock_session
            
            response = client.get("/users/nonexistent")
            
            assert response.status_code == 404
            assert "not found" in response.json()["detail"]
    
    def test_update_user_preferences_success(self):
        """Test successful user preferences update."""
        with patch.object(app.dependency_overrides, 'clear'), \
             patch('story_engine.service.get_db') as mock_db:
            
            # Mock user
            mock_user = Mock()
            mock_user.user_id = "testuser"
            mock_user.email_notifications = True
            mock_user.webpush_notifications = True
            mock_user.email_address = "old@example.com"
            
            mock_session = Mock()
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user
            mock_db.return_value = mock_session
            
            preferences = {
                "email_notifications": False,
                "email_address": "new@example.com"
            }
            
            response = client.patch("/users/testuser/preferences", json=preferences)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert mock_user.email_notifications is False
            assert mock_user.email_address == "new@example.com"
    
    def test_update_preferences_user_not_found(self):
        """Test preferences update with non-existent user.""" 
        with patch.object(app.dependency_overrides, 'clear'), \
             patch('story_engine.service.get_db') as mock_db:
            
            mock_session = Mock()
            mock_session.query.return_value.filter.return_value.first.return_value = None
            mock_db.return_value = mock_session
            
            response = client.patch("/users/nonexistent/preferences", json={"email_notifications": False})
            
            assert response.status_code == 404
            assert "not found" in response.json()["detail"]


class TestOpenAPICompliance:
    """Test OpenAPI schema and documentation compliance."""
    
    def test_openapi_schema_available(self):
        """Test that OpenAPI schema is available."""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
    
    def test_docs_available(self):
        """Test that interactive API docs are available."""
        response = client.get("/docs")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_all_endpoints_documented(self):
        """Test that all endpoints are documented in OpenAPI schema."""
        response = client.get("/openapi.json")
        schema = response.json()
        paths = schema["paths"]
        
        # Required endpoints from Feature 7
        required_endpoints = [
            "/ingest/sample",
            "/recognize", 
            "/aggregator/summary",
            "/characters",
            "/characters/{character_id}",
            "/users",
            "/users/{user_id}",
            "/users/{user_id}/preferences",
            "/notifications/subscribe"  # From previous feature
        ]
        
        for endpoint in required_endpoints:
            # Check if exact endpoint exists or parameterized version
            endpoint_exists = (
                endpoint in paths or 
                any(endpoint.replace("{character_id}", "{id}") in path or
                    endpoint.replace("{user_id}", "{id}") in path for path in paths.keys()) or
                any(endpoint.split("/")[-1] in path for path in paths.keys())
            )
            assert endpoint_exists, f"Endpoint {endpoint} not documented in OpenAPI schema"
    
    def test_response_models_defined(self):
        """Test that response models are properly defined."""
        response = client.get("/openapi.json")
        schema = response.json()
        
        # Should have components/schemas section
        assert "components" in schema
        assert "schemas" in schema["components"]
        
        # Check for key models
        schemas = schema["components"]["schemas"]
        expected_models = [
            "SampleRequest",
            "RecognitionEvent", 
            "CharacterUpdate",
            "UserCreate",
            "UserUpdate"
        ]
        
        for model in expected_models:
            assert model in schemas, f"Model {model} not defined in OpenAPI schema"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])