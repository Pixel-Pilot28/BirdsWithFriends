"""
Test script to verify the story scheduling functionality.

This script tests the core scheduling features:
1. Story creation with scheduling
2. Episode publishing schedule
3. Scheduler API endpoints
"""
import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

import httpx
import pytest


class TestStoryScheduling:
    """Test cases for story scheduling features."""
    
    BASE_URL = "http://localhost:8005"
    
    @pytest.fixture
    async def client(self):
        """HTTP client for API testing."""
        async with httpx.AsyncClient(base_url=self.BASE_URL) as client:
            yield client
    
    def create_test_story_request(self) -> Dict[str, Any]:
        """Create a test story request with bird data."""
        return {
            "story_request": {
                "user_id": "test_user_123",
                "time_range": {
                    "start": "2024-01-15T08:00:00Z",
                    "end": "2024-01-15T18:00:00Z"
                },
                "species_counts": [
                    {
                        "species": "Northern Cardinal",
                        "count": 5,
                        "confidence": 0.95
                    },
                    {
                        "species": "Blue Jay",
                        "count": 3,
                        "confidence": 0.88
                    }
                ],
                "characters": [
                    {
                        "id": "cardinal_1",
                        "species": "Northern Cardinal",
                        "archetype": "Wise Leader",
                        "name": "Charlie",
                        "appearance_count": 3
                    },
                    {
                        "id": "bluejay_1",
                        "species": "Blue Jay",
                        "archetype": "Curious Explorer",
                        "name": "Jay",
                        "appearance_count": 2
                    }
                ],
                "user_prefs": {
                    "story_type": "Adventure",
                    "age_group": "school_age",
                    "include_morals": True,
                    "content_rating": "G"
                },
                "life_lessons": ["teamwork", "friendship"],
                "length": "medium",
                "episodes": 3
            }
        }
    
    @pytest.mark.asyncio
    async def test_create_story_without_schedule(self, client):
        """Test creating a story without scheduling (immediate release)."""
        
        story_request = self.create_test_story_request()
        
        response = await client.post("/stories", json=story_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "story_id" in data
        assert data["total_episodes"] == 3
        assert data["status"] == "created"
        assert "serialized" not in data  # Should not be serialized
        
        return data["story_id"]
    
    @pytest.mark.asyncio
    async def test_create_story_with_schedule(self, client):
        """Test creating a story with serialized scheduling."""
        
        story_request = self.create_test_story_request()
        
        # Add scheduling information
        start_date = datetime.now(timezone.utc) + timedelta(hours=1)  # Start in 1 hour
        story_request["schedule"] = {
            "start_date": start_date.isoformat(),
            "release_frequency": "daily",
            "timezone": "UTC"
        }
        
        response = await client.post("/stories", json=story_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "story_id" in data
        assert data["serialized"] is True
        assert data["release_frequency"] == "daily"
        assert data["timezone"] == "UTC"
        
        return data["story_id"]
    
    @pytest.mark.asyncio
    async def test_schedule_existing_story(self, client):
        """Test scheduling an existing story."""
        
        # First create a story without scheduling
        story_id = await self.test_create_story_without_schedule(client)
        
        # Wait a moment for episodes to be generated
        await asyncio.sleep(2)
        
        # Schedule the story
        start_date = datetime.now(timezone.utc) + timedelta(hours=2)
        schedule_request = {
            "story_id": story_id,
            "start_date": start_date.isoformat(),
            "release_frequency": "weekly",
            "timezone": "America/New_York"
        }
        
        response = await client.post(f"/stories/{story_id}/schedule", json=schedule_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["scheduled"] is True
        assert data["release_frequency"] == "weekly"
        assert data["timezone"] == "America/New_York"
    
    @pytest.mark.asyncio
    async def test_get_story_schedule(self, client):
        """Test retrieving story schedule information."""
        
        # Create a scheduled story
        story_id = await self.test_create_story_with_schedule(client)
        
        # Wait for setup to complete
        await asyncio.sleep(3)
        
        # Get schedule info
        response = await client.get(f"/stories/{story_id}/schedule")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["story_id"] == story_id
        assert data["is_serialized"] is True
        assert data["release_frequency"] == "daily"
        assert "next_release_at" in data
    
    @pytest.mark.asyncio
    async def test_cancel_story_schedule(self, client):
        """Test cancelling a story's schedule."""
        
        # Create a scheduled story
        story_id = await self.test_create_story_with_schedule(client)
        
        # Wait for setup to complete
        await asyncio.sleep(3)
        
        # Cancel the schedule
        response = await client.delete(f"/stories/{story_id}/schedule")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "cancelled"
        assert "cancelled_jobs" in data
    
    @pytest.mark.asyncio
    async def test_scheduler_status(self, client):
        """Test getting scheduler status."""
        
        response = await client.get("/scheduler/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "scheduler_running" in data
        assert "total_scheduled_jobs" in data
        assert "jobs" in data
        assert "timestamp" in data
    
    @pytest.mark.asyncio
    async def test_health_check_with_scheduler(self, client):
        """Test health check includes scheduler status."""
        
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "scheduler_running" in data


def run_manual_tests():
    """Run manual tests for development verification."""
    
    async def main():
        async with httpx.AsyncClient(base_url="http://localhost:8005") as client:
            
            print("🧪 Testing Story Scheduling Features")
            print("=" * 50)
            
            # Test 1: Health check
            print("\n1. Testing health check...")
            try:
                response = await client.get("/health")
                print(f"✅ Health: {response.json()['status']}")
            except Exception as e:
                print(f"❌ Health check failed: {e}")
                return
            
            # Test 2: Scheduler status
            print("\n2. Testing scheduler status...")
            try:
                response = await client.get("/scheduler/status")
                status = response.json()
                print(f"✅ Scheduler running: {status['scheduler_running']}")
                print(f"   Active jobs: {status['total_scheduled_jobs']}")
            except Exception as e:
                print(f"❌ Scheduler status failed: {e}")
            
            # Test 3: Create scheduled story
            print("\n3. Creating scheduled story...")
            try:
                test_class = TestStoryScheduling()
                story_request = test_class.create_test_story_request()
                
                start_date = datetime.now(timezone.utc) + timedelta(minutes=5)
                story_request["schedule"] = {
                    "start_date": start_date.isoformat(),
                    "release_frequency": "daily",
                    "timezone": "UTC"
                }
                
                response = await client.post("/stories", json=story_request)
                if response.status_code == 200:
                    data = response.json()
                    story_id = data["story_id"]
                    print(f"✅ Created scheduled story: {story_id}")
                    print(f"   Episodes: {data['total_episodes']}")
                    print(f"   Start date: {data.get('start_date', 'N/A')}")
                    
                    # Wait and check schedule
                    print("\n   Waiting for episodes to generate...")
                    await asyncio.sleep(5)
                    
                    schedule_response = await client.get(f"/stories/{story_id}/schedule")
                    if schedule_response.status_code == 200:
                        schedule_data = schedule_response.json()
                        print(f"   Schedule active: {schedule_data['is_serialized']}")
                        print(f"   Next release: {schedule_data.get('next_release_at', 'N/A')}")
                    
                else:
                    print(f"❌ Story creation failed: {response.status_code}")
                    print(response.text)
            except Exception as e:
                print(f"❌ Scheduled story test failed: {e}")
            
            print("\n🎉 Manual testing complete!")
    
    asyncio.run(main())


if __name__ == "__main__":
    print("Run with pytest for automated tests or call run_manual_tests() for manual testing")
    # Uncomment to run manual tests:
    # run_manual_tests()