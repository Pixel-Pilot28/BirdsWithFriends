#!/usr/bin/env python3
"""
Development runner for the Birds with Friends sampler service.
"""
import uvicorn
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from ingest.config import settings

if __name__ == "__main__":
    print("Starting Birds with Friends - Sampler Service")
    print(f"Host: {settings.host}:{settings.port}")
    print(f"Debug: {settings.debug}")
    print(f"Output directory: {settings.output_dir}")
    print(f"Cornell cam URL: {settings.cornell_cam_url}")
    print("-" * 50)
    
    uvicorn.run(
        "ingest.sampler:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if settings.debug else "warning"
    )