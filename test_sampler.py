#!/usr/bin/env python3
"""
Test script for the Birds with Friends sampler service.
"""
import time
import requests
import sys
from pathlib import Path


def test_service_health():
    """Test the health endpoint."""
    print("Testing service health...")
    
    try:
        response = requests.get("http://localhost:8000/health", timeout=10)
        response.raise_for_status()
        
        health_data = response.json()
        print(f"✓ Health check passed: {health_data['status']}")
        print(f"  - FFmpeg available: {health_data['ffmpeg_available']}")
        return True
        
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False


def test_sample_capture():
    """Test the sample capture endpoint."""
    print("\nTesting sample capture...")
    
    try:
        # Use a shorter duration for testing
        response = requests.post(
            "http://localhost:8000/dev/ingest/test-sample",
            params={"duration": 2},  # Short audio clip for testing
            timeout=60  # Give enough time for capture
        )
        response.raise_for_status()
        
        sample_data = response.json()
        print(f"✓ Sample capture successful:")
        print(f"  - Timestamp: {sample_data['timestamp']}")
        print(f"  - Snapshot: {Path(sample_data['snapshot_url']).name}")
        print(f"  - Audio: {Path(sample_data['audio_url']).name}")
        print(f"  - Duration: {sample_data['duration']}s")
        
        # Verify files exist
        snapshot_path = Path(sample_data['snapshot_url'])
        audio_path = Path(sample_data['audio_url'])
        
        if snapshot_path.exists():
            print(f"  - Snapshot file exists ({snapshot_path.stat().st_size} bytes)")
        else:
            print(f"  - ⚠ Snapshot file not found: {snapshot_path}")
            
        if audio_path.exists():
            print(f"  - Audio file exists ({audio_path.stat().st_size} bytes)")
        else:
            print(f"  - ⚠ Audio file not found: {audio_path}")
        
        return True
        
    except Exception as e:
        print(f"✗ Sample capture failed: {e}")
        return False


def main():
    """Run all tests."""
    print("Birds with Friends - Sampler Service Test")
    print("=" * 45)
    
    # Wait for service to be ready
    print("Waiting for service to be ready...")
    for i in range(30):  # Wait up to 30 seconds
        try:
            requests.get("http://localhost:8000/health", timeout=2)
            break
        except:
            print(f"  Attempt {i+1}/30...")
            time.sleep(1)
    else:
        print("✗ Service did not become ready in time")
        sys.exit(1)
    
    # Run tests
    health_ok = test_service_health()
    sample_ok = test_sample_capture()
    
    print("\n" + "=" * 45)
    if health_ok and sample_ok:
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()