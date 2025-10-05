"""
Test script for Birds with Friends event flow.

Tests the integration between recognition services and the aggregator.
"""
import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any

import httpx


class EventFlowTester:
    """Test event flow between services."""
    
    def __init__(self):
        self.base_urls = {
            'sampler': 'http://localhost:8001',
            'audio': 'http://localhost:8002',
            'image': 'http://localhost:8003',
            'aggregator': 'http://localhost:8004'
        }
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def test_service_health(self):
        """Test that all services are healthy."""
        print("Testing service health...")
        
        results = {}
        for service, url in self.base_urls.items():
            try:
                response = await self.client.get(f"{url}/health")
                results[service] = {
                    'status': response.status_code,
                    'healthy': response.status_code == 200
                }
                print(f"  {service}: {'✓' if results[service]['healthy'] else '✗'} ({response.status_code})")
            except Exception as e:
                results[service] = {'status': 'error', 'healthy': False, 'error': str(e)}
                print(f"  {service}: ✗ Error - {e}")
        
        return results
    
    async def test_recognition_to_aggregator_flow(self):
        """Test recognition event to aggregator flow."""
        print("\nTesting recognition -> aggregator event flow...")
        
        # Test data - simulate recognition events
        test_events = [
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "audio",
                "detections": [
                    {
                        "species": "Northern Cardinal",
                        "count": 2,
                        "confidence": 0.85,
                        "low_confidence": False
                    }
                ],
                "snapshot_url": "test://audio_snapshot_1"
            },
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "image",
                "detections": [
                    {
                        "species": "Blue Jay", 
                        "count": 1,
                        "confidence": 0.92,
                        "low_confidence": False,
                        "bbox": [100, 50, 200, 150]
                    },
                    {
                        "species": "American Robin",
                        "count": 3,
                        "confidence": 0.78,
                        "low_confidence": False,
                        "bbox": [300, 200, 400, 300]
                    }
                ],
                "snapshot_url": "test://image_snapshot_1"
            }
        ]
        
        # Send events to aggregator
        for i, event in enumerate(test_events):
            try:
                response = await self.client.post(
                    f"{self.base_urls['aggregator']}/events",
                    json=event
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"  Event {i+1}: ✓ Processed - {result['characters_affected']} characters affected")
                    print(f"    Character IDs: {result['character_ids']}")
                else:
                    print(f"  Event {i+1}: ✗ Failed ({response.status_code}) - {response.text}")
                
            except Exception as e:
                print(f"  Event {i+1}: ✗ Error - {e}")
        
        # Allow time for processing
        await asyncio.sleep(1)
    
    async def test_aggregator_endpoints(self):
        """Test aggregator API endpoints."""
        print("\nTesting aggregator API endpoints...")
        
        # Test /summary endpoint
        try:
            response = await self.client.get(f"{self.base_urls['aggregator']}/summary")
            if response.status_code == 200:
                summary = response.json()
                print(f"  /summary: ✓ Success - {len(summary['characters'])} characters, {len(summary['species'])} species")
                print(f"    Species: {summary['species']}")
            else:
                print(f"  /summary: ✗ Failed ({response.status_code})")
        except Exception as e:
            print(f"  /summary: ✗ Error - {e}")
        
        # Test /characters endpoint
        try:
            response = await self.client.get(f"{self.base_urls['aggregator']}/characters")
            if response.status_code == 200:
                characters = response.json()
                print(f"  /characters: ✓ Success - {len(characters)} characters")
                for char in characters[:3]:  # Show first 3
                    print(f"    - {char['id']}: {char['species']} ({char['archetype']}) - seen {char['appearance_count']} times")
            else:
                print(f"  /characters: ✗ Failed ({response.status_code})")
        except Exception as e:
            print(f"  /characters: ✗ Error - {e}")
        
        # Test /stats endpoint
        try:
            response = await self.client.get(f"{self.base_urls['aggregator']}/stats")
            if response.status_code == 200:
                stats = response.json()
                print(f"  /stats: ✓ Success - {stats['total_characters']} total characters")
                print(f"    Species breakdown: {stats['species_counts']}")
            else:
                print(f"  /stats: ✗ Failed ({response.status_code})")
        except Exception as e:
            print(f"  /stats: ✗ Error - {e}")
    
    async def test_recognition_services(self):
        """Test recognition services directly."""
        print("\nTesting recognition services...")
        
        # Test audio recognition
        test_audio_data = {
            "audio_file": "test_audio.wav",
            "duration": 5.0
        }
        
        try:
            response = await self.client.post(
                f"{self.base_urls['audio']}/recognize",
                json=test_audio_data
            )
            if response.status_code == 200:
                result = response.json()
                print(f"  Audio recognition: ✓ Success - {len(result['detections'])} detections")
            else:
                print(f"  Audio recognition: ✗ Failed ({response.status_code})")
        except Exception as e:
            print(f"  Audio recognition: ✗ Error - {e}")
        
        # Test image recognition
        test_image_data = {
            "image_file": "test_image.jpg"
        }
        
        try:
            response = await self.client.post(
                f"{self.base_urls['image']}/recognize",
                json=test_image_data
            )
            if response.status_code == 200:
                result = response.json()
                print(f"  Image recognition: ✓ Success - {len(result['detections'])} detections")
            else:
                print(f"  Image recognition: ✗ Failed ({response.status_code})")
        except Exception as e:
            print(f"  Image recognition: ✗ Error - {e}")
    
    async def test_character_updates(self):
        """Test character update functionality."""
        print("\nTesting character update functionality...")
        
        # First get a character to update
        try:
            response = await self.client.get(f"{self.base_urls['aggregator']}/characters?limit=1")
            if response.status_code == 200:
                characters = response.json()
                if characters:
                    char_id = characters[0]['id']
                    
                    # Test character update
                    update_data = {
                        "name": "Test Bird",
                        "personality_notes": "Very friendly and social"
                    }
                    
                    response = await self.client.patch(
                        f"{self.base_urls['aggregator']}/characters/{char_id}",
                        json=update_data
                    )
                    
                    if response.status_code == 200:
                        updated = response.json()
                        print(f"  Character update: ✓ Success - Updated {char_id}")
                        print(f"    Name: {updated['name']}")
                        print(f"    Notes: {updated['personality_notes']}")
                    else:
                        print(f"  Character update: ✗ Failed ({response.status_code})")
                else:
                    print("  Character update: ⚠ No characters to update")
            else:
                print(f"  Character update: ✗ Failed to get characters ({response.status_code})")
        except Exception as e:
            print(f"  Character update: ✗ Error - {e}")
    
    async def run_full_test_suite(self):
        """Run complete test suite."""
        print("🐦 Birds with Friends - Event Flow Integration Tests")
        print("=" * 60)
        
        try:
            # Test service health
            health_results = await self.test_service_health()
            
            # Only proceed if core services are healthy
            if not all(health_results[svc]['healthy'] for svc in ['aggregator']):
                print("\n❌ Core services are not healthy. Stopping tests.")
                return
            
            # Test recognition services
            await self.test_recognition_services()
            
            # Test event flow
            await self.test_recognition_to_aggregator_flow()
            
            # Test aggregator endpoints
            await self.test_aggregator_endpoints()
            
            # Test character updates
            await self.test_character_updates()
            
            print("\n🎉 Test suite completed!")
            
        finally:
            await self.client.aclose()
    
    async def interactive_test_session(self):
        """Run interactive testing session."""
        print("🐦 Birds with Friends - Interactive Test Session")
        print("Available commands:")
        print("  1. Health check")
        print("  2. Send test event")
        print("  3. Get summary")
        print("  4. List characters") 
        print("  5. Get stats")
        print("  q. Quit")
        
        try:
            while True:
                command = input("\nEnter command (1-5, q): ").strip().lower()
                
                if command == 'q':
                    break
                elif command == '1':
                    await self.test_service_health()
                elif command == '2':
                    await self.test_recognition_to_aggregator_flow()
                elif command == '3':
                    try:
                        response = await self.client.get(f"{self.base_urls['aggregator']}/summary")
                        if response.status_code == 200:
                            summary = response.json()
                            print(json.dumps(summary, indent=2))
                        else:
                            print(f"Failed: {response.status_code}")
                    except Exception as e:
                        print(f"Error: {e}")
                elif command == '4':
                    try:
                        response = await self.client.get(f"{self.base_urls['aggregator']}/characters")
                        if response.status_code == 200:
                            characters = response.json()
                            for char in characters:
                                print(f"{char['id']}: {char['species']} ({char['appearance_count']} appearances)")
                        else:
                            print(f"Failed: {response.status_code}")
                    except Exception as e:
                        print(f"Error: {e}")
                elif command == '5':
                    try:
                        response = await self.client.get(f"{self.base_urls['aggregator']}/stats")
                        if response.status_code == 200:
                            stats = response.json()
                            print(json.dumps(stats, indent=2))
                        else:
                            print(f"Failed: {response.status_code}")
                    except Exception as e:
                        print(f"Error: {e}")
                else:
                    print("Invalid command. Try again.")
                    
        finally:
            await self.client.aclose()


async def main():
    """Main function."""
    import sys
    
    tester = EventFlowTester()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--interactive':
        await tester.interactive_test_session()
    else:
        await tester.run_full_test_suite()


if __name__ == "__main__":
    asyncio.run(main())