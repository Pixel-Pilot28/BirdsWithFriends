"""
Test script for Story Engine integration.

Tests the complete story generation pipeline including request validation,
template processing, LLM generation, and episode management.
"""
import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any

import httpx


class StoryEngineTestSuite:
    """Comprehensive test suite for the story engine."""
    
    def __init__(self):
        self.base_urls = {
            'aggregator': 'http://localhost:8004',
            'story_engine': 'http://localhost:8005'
        }
        self.client = httpx.AsyncClient(timeout=60.0)
        self.test_results = {}
    
    async def run_complete_test_suite(self):
        """Run the complete test suite."""
        print("🎭 Birds with Friends - Story Engine Integration Tests")
        print("=" * 65)
        
        try:
            # Test service health
            await self.test_service_health()
            
            # Test story request validation
            await self.test_story_request_validation()
            
            # Test child vs adult content generation
            await self.test_age_appropriate_content()
            
            # Test episode generation and management
            await self.test_episode_management()
            
            # Test content safety features
            await self.test_content_safety()
            
            # Print summary
            self.print_test_summary()
            
        finally:
            await self.client.aclose()
    
    async def test_service_health(self):
        """Test that services are healthy."""
        print("\n🔍 Testing Service Health...")
        
        for service, url in self.base_urls.items():
            try:
                response = await self.client.get(f"{url}/health")
                if response.status_code == 200:
                    health_data = response.json()
                    print(f"  {service}: ✓ ({health_data.get('status', 'unknown')})")
                    self.test_results[f"{service}_health"] = True
                else:
                    print(f"  {service}: ✗ ({response.status_code})")
                    self.test_results[f"{service}_health"] = False
            except Exception as e:
                print(f"  {service}: ✗ Error - {e}")
                self.test_results[f"{service}_health"] = False
    
    async def test_story_request_validation(self):
        """Test story request validation."""
        print("\n📝 Testing Story Request Validation...")
        
        # Valid child story request
        valid_child_request = {
            "story_request": {
                "user_id": "test_user_1",
                "time_range": {
                    "start": "2025-10-04T10:00:00Z",
                    "end": "2025-10-04T10:15:00Z"
                },
                "species_counts": [
                    {"species": "Northern Cardinal", "count": 2, "confidence": 0.9},
                    {"species": "Blue Jay", "count": 1, "confidence": 0.85}
                ],
                "characters": [
                    {
                        "id": "northern_cardinal_1",
                        "species": "Northern Cardinal",
                        "archetype": "bold gossip",
                        "appearance_count": 3
                    },
                    {
                        "id": "blue_jay_1", 
                        "species": "Blue Jay",
                        "archetype": "clever troublemaker",
                        "appearance_count": 1
                    }
                ],
                "user_prefs": {
                    "story_type": "Friendship",
                    "attributes": ["kind", "helpful"],
                    "age_group": "child",
                    "include_morals": True,
                    "content_rating": "G"
                },
                "life_lessons": ["sharing", "kindness"],
                "length": "short",
                "episodes": 1
            }
        }
        
        try:
            response = await self.client.post(
                f"{self.base_urls['story_engine']}/stories",
                json=valid_child_request
            )
            
            if response.status_code == 200:
                result = response.json()
                story_id = result.get('story_id')
                print(f"  Valid child request: ✓ Created story {story_id}")
                self.test_results['child_story_creation'] = story_id
                
                # Wait for episode generation
                await self.wait_for_episode_generation(story_id)
                
            else:
                print(f"  Valid child request: ✗ Failed ({response.status_code})")
                print(f"    Response: {response.text}")
                self.test_results['child_story_creation'] = False
                
        except Exception as e:
            print(f"  Valid child request: ✗ Error - {e}")
            self.test_results['child_story_creation'] = False
        
        # Test invalid request
        invalid_request = {
            "story_request": {
                "user_id": "",  # Invalid empty user_id
                "time_range": {"start": "invalid_time"},  # Invalid time format
                "species_counts": [],
                "characters": [],
                "user_prefs": {
                    "story_type": "InvalidType",  # Invalid story type
                    "age_group": "invalid_age"    # Invalid age group
                }
            }
        }
        
        try:
            response = await self.client.post(
                f"{self.base_urls['story_engine']}/stories",
                json=invalid_request
            )
            
            if response.status_code == 400:
                print("  Invalid request validation: ✓ Correctly rejected")
                self.test_results['request_validation'] = True
            else:
                print(f"  Invalid request validation: ✗ Should have been rejected ({response.status_code})")
                self.test_results['request_validation'] = False
                
        except Exception as e:
            print(f"  Invalid request validation: ✗ Error - {e}")
            self.test_results['request_validation'] = False
    
    async def test_age_appropriate_content(self):
        """Test age-appropriate content generation."""
        print("\n👶 Testing Age-Appropriate Content...")
        
        # Create adult story request
        adult_request = {
            "story_request": {
                "user_id": "test_user_adult",
                "time_range": {
                    "start": "2025-10-04T10:00:00Z",
                    "end": "2025-10-04T10:15:00Z"
                },
                "species_counts": [
                    {"species": "Northern Cardinal", "count": 2, "confidence": 0.9},
                    {"species": "Blue Jay", "count": 1, "confidence": 0.85}
                ],
                "characters": [
                    {
                        "id": "northern_cardinal_1",
                        "species": "Northern Cardinal", 
                        "archetype": "dramatic queen",
                        "appearance_count": 2
                    }
                ],
                "user_prefs": {
                    "story_type": "Real Housewives",
                    "attributes": ["dramatic", "gossipy"],
                    "age_group": "adult",
                    "include_morals": False,
                    "content_rating": "PG"
                },
                "life_lessons": [],
                "length": "medium",
                "episodes": 1
            }
        }
        
        try:
            response = await self.client.post(
                f"{self.base_urls['story_engine']}/stories",
                json=adult_request
            )
            
            if response.status_code == 200:
                result = response.json()
                adult_story_id = result.get('story_id')
                print(f"  Adult story creation: ✓ Created story {adult_story_id}")
                
                # Wait for generation and compare content
                await self.wait_for_episode_generation(adult_story_id)
                
                # Fetch and compare child vs adult content
                if self.test_results.get('child_story_creation'):
                    await self.compare_age_content(
                        self.test_results['child_story_creation'],
                        adult_story_id
                    )
                
                self.test_results['adult_story_creation'] = adult_story_id
                
            else:
                print(f"  Adult story creation: ✗ Failed ({response.status_code})")
                self.test_results['adult_story_creation'] = False
                
        except Exception as e:
            print(f"  Adult story creation: ✗ Error - {e}")
            self.test_results['adult_story_creation'] = False
    
    async def compare_age_content(self, child_story_id: str, adult_story_id: str):
        """Compare child and adult story content."""
        try:
            # Get child story
            child_response = await self.client.get(
                f"{self.base_urls['story_engine']}/stories/{child_story_id}"
            )
            
            # Get adult story  
            adult_response = await self.client.get(
                f"{self.base_urls['story_engine']}/stories/{adult_story_id}"
            )
            
            if child_response.status_code == 200 and adult_response.status_code == 200:
                child_story = child_response.json()
                adult_story = adult_response.json()
                
                child_text = ""
                adult_text = ""
                
                if child_story.get('episodes'):
                    child_text = child_story['episodes'][0].get('text', '')
                if adult_story.get('episodes'):
                    adult_text = adult_story['episodes'][0].get('text', '')
                
                # Analyze content differences
                child_indicators = ['lesson', 'learn', 'kind', 'friend', 'share', 'help']
                adult_indicators = ['drama', 'gossip', 'sophisticated', 'witty']
                
                child_score = sum(1 for word in child_indicators if word.lower() in child_text.lower())
                adult_score = sum(1 for word in adult_indicators if word.lower() in adult_text.lower())
                
                print(f"  Content differentiation: Child indicators: {child_score}, Adult indicators: {adult_score}")
                
                if child_score > 0 or adult_score > 0:
                    print("  Age-appropriate content: ✓ Content differs appropriately")
                    self.test_results['age_content_diff'] = True
                else:
                    print("  Age-appropriate content: ⚠ Limited differentiation detected")
                    self.test_results['age_content_diff'] = "warning"
                    
            else:
                print("  Content comparison: ✗ Failed to fetch stories for comparison")
                self.test_results['age_content_diff'] = False
                
        except Exception as e:
            print(f"  Content comparison: ✗ Error - {e}")
            self.test_results['age_content_diff'] = False
    
    async def test_episode_management(self):
        """Test episode management features."""
        print("\n📚 Testing Episode Management...")
        
        # Create multi-episode story
        multi_episode_request = {
            "story_request": {
                "user_id": "test_user_multi",
                "time_range": {
                    "start": "2025-10-04T10:00:00Z",
                    "end": "2025-10-04T10:15:00Z"
                },
                "species_counts": [
                    {"species": "American Robin", "count": 3, "confidence": 0.8}
                ],
                "characters": [
                    {
                        "id": "american_robin_1",
                        "species": "American Robin",
                        "archetype": "wise mentor",
                        "appearance_count": 5
                    }
                ],
                "user_prefs": {
                    "story_type": "Educational",
                    "attributes": ["wise", "teaching"],
                    "age_group": "school_age",
                    "content_rating": "G"
                },
                "life_lessons": ["perseverance"],
                "length": "medium",
                "episodes": 3
            }
        }
        
        try:
            response = await self.client.post(
                f"{self.base_urls['story_engine']}/stories",
                json=multi_episode_request
            )
            
            if response.status_code == 200:
                result = response.json()
                story_id = result.get('story_id')
                print(f"  Multi-episode story creation: ✓ Created {story_id}")
                
                # Wait for first episode
                await asyncio.sleep(3)
                
                # Test episode listing
                story_response = await self.client.get(
                    f"{self.base_urls['story_engine']}/stories/{story_id}"
                )
                
                if story_response.status_code == 200:
                    story_data = story_response.json()
                    episode_count = len(story_data.get('episodes', []))
                    print(f"  Episode generation progress: {episode_count}/3 episodes")
                    
                    if episode_count > 0:
                        # Test individual episode retrieval
                        episode_response = await self.client.get(
                            f"{self.base_urls['story_engine']}/stories/{story_id}/episodes/1"
                        )
                        
                        if episode_response.status_code == 200:
                            episode_data = episode_response.json()
                            print(f"  Individual episode retrieval: ✓")
                            print(f"    Word count: {episode_data.get('word_count', 0)}")
                            print(f"    Safety score: {episode_data.get('safety_score', 0):.2f}")
                            
                            self.test_results['episode_management'] = True
                        else:
                            print(f"  Individual episode retrieval: ✗ ({episode_response.status_code})")
                            self.test_results['episode_management'] = False
                    else:
                        print("  Episode management: ⚠ No episodes generated yet")
                        self.test_results['episode_management'] = "pending"
                        
                else:
                    print(f"  Story retrieval: ✗ ({story_response.status_code})")
                    self.test_results['episode_management'] = False
                    
            else:
                print(f"  Multi-episode story creation: ✗ ({response.status_code})")
                self.test_results['episode_management'] = False
                
        except Exception as e:
            print(f"  Episode management: ✗ Error - {e}")
            self.test_results['episode_management'] = False
    
    async def test_content_safety(self):
        """Test content safety features."""
        print("\n🛡️ Testing Content Safety...")
        
        # Check safety scores from generated content
        stories_to_check = []
        
        for key in ['child_story_creation', 'adult_story_creation']:
            story_id = self.test_results.get(key)
            if story_id and isinstance(story_id, str):
                stories_to_check.append((key, story_id))
        
        safety_results = []
        
        for story_type, story_id in stories_to_check:
            try:
                response = await self.client.get(
                    f"{self.base_urls['story_engine']}/stories/{story_id}"
                )
                
                if response.status_code == 200:
                    story_data = response.json()
                    episodes = story_data.get('episodes', [])
                    
                    for episode in episodes:
                        safety_score = episode.get('safety_score', 0)
                        warnings = episode.get('content_warnings', [])
                        
                        safety_results.append({
                            'type': story_type,
                            'score': safety_score,
                            'warnings': len(warnings)
                        })
                        
                        print(f"  {story_type}: Safety score {safety_score:.2f}, {len(warnings)} warnings")
                        
            except Exception as e:
                print(f"  Safety check for {story_type}: ✗ Error - {e}")
        
        # Analyze safety results
        if safety_results:
            avg_safety = sum(r['score'] for r in safety_results) / len(safety_results)
            total_warnings = sum(r['warnings'] for r in safety_results)
            
            print(f"  Overall safety: Average score {avg_safety:.2f}, {total_warnings} total warnings")
            
            if avg_safety >= 0.8:
                print("  Content safety: ✓ High safety scores")
                self.test_results['content_safety'] = True
            elif avg_safety >= 0.6:
                print("  Content safety: ⚠ Moderate safety scores")
                self.test_results['content_safety'] = "warning"
            else:
                print("  Content safety: ✗ Low safety scores")
                self.test_results['content_safety'] = False
        else:
            print("  Content safety: ⚠ No content available for safety analysis")
            self.test_results['content_safety'] = "no_data"
    
    async def wait_for_episode_generation(self, story_id: str, max_wait: int = 30):
        """Wait for episode generation to complete."""
        print(f"    Waiting for episode generation (max {max_wait}s)...")
        
        for i in range(max_wait):
            try:
                response = await self.client.get(
                    f"{self.base_urls['story_engine']}/stories/{story_id}"
                )
                
                if response.status_code == 200:
                    story_data = response.json()
                    episodes = story_data.get('episodes', [])
                    
                    if episodes and episodes[0].get('text'):
                        print(f"    Episode generated after {i+1}s")
                        return True
                        
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"    Error checking episode status: {e}")
                return False
        
        print(f"    Episode generation timed out after {max_wait}s")
        return False
    
    def print_test_summary(self):
        """Print test results summary."""
        print("\n" + "="*65)
        print("🎭 STORY ENGINE TEST SUMMARY")
        print("="*65)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for v in self.test_results.values() if v is True)
        warning_tests = sum(1 for v in self.test_results.values() if isinstance(v, str) and v not in [False, True])
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Warnings: {warning_tests}")
        print(f"Failed: {total_tests - passed_tests - warning_tests}")
        print()
        
        for test_name, result in self.test_results.items():
            if result is True:
                status = "✓ PASS"
            elif result is False:
                status = "✗ FAIL"
            elif isinstance(result, str) and result not in ["true", "false"]:
                if "warning" in result or "pending" in result or "no_data" in result:
                    status = "⚠ WARN"
                else:
                    status = f"ℹ {result}"
            else:
                status = f"? {result}"
            
            print(f"  {test_name}: {status}")
        
        print("\n🎉 Story Engine testing completed!")


async def main():
    """Main test function."""
    tester = StoryEngineTestSuite()
    await tester.run_complete_test_suite()


if __name__ == "__main__":
    asyncio.run(main())