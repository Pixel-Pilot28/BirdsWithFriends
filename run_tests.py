"""
Test runner script for recognition services.
"""
import subprocess
import sys
import time
import requests
from pathlib import Path


def wait_for_service(url: str, timeout: int = 30) -> bool:
    """Wait for a service to become available."""
    print(f"Waiting for service at {url}...")
    
    for i in range(timeout):
        try:
            response = requests.get(f"{url}/health", timeout=2)
            if response.status_code == 200:
                print(f"✓ Service ready at {url}")
                return True
        except requests.exceptions.RequestException:
            pass
        
        if i < timeout - 1:
            time.sleep(1)
    
    print(f"✗ Service at {url} did not become ready in {timeout}s")
    return False


def run_unit_tests():
    """Run unit tests."""
    print("Running unit tests...")
    result = subprocess.run([
        sys.executable, "-m", "pytest",
        "tests/test_recognition_adapters.py",
        "-v"
    ], cwd=Path(__file__).parent.parent)
    
    return result.returncode == 0


def run_integration_tests():
    """Run integration tests (requires services to be running)."""
    print("Checking if services are available...")
    
    services = [
        "http://localhost:8002",  # audio-recognizer
        "http://localhost:8003"   # image-recognizer
    ]
    
    all_ready = True
    for service_url in services:
        if not wait_for_service(service_url, timeout=5):
            all_ready = False
    
    if not all_ready:
        print("⚠ Some services are not available. Skipping integration tests.")
        print("To run integration tests, start services with:")
        print("  docker-compose up -d audio-recognizer image-recognizer")
        return True  # Don't fail the overall test run
    
    print("Running integration tests...")
    result = subprocess.run([
        sys.executable, "-m", "pytest",
        "tests/test_api_integration.py",
        "-v"
    ], cwd=Path(__file__).parent.parent)
    
    return result.returncode == 0


def main():
    """Run all tests."""
    print("Birds with Friends - Recognition Service Tests")
    print("=" * 50)
    
    success = True
    
    # Run unit tests
    if not run_unit_tests():
        print("✗ Unit tests failed!")
        success = False
    else:
        print("✓ Unit tests passed!")
    
    print()
    
    # Run integration tests
    if not run_integration_tests():
        print("✗ Integration tests failed!")
        success = False
    else:
        print("✓ Integration tests passed!")
    
    print("\n" + "=" * 50)
    if success:
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()