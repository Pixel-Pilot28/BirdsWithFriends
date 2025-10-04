"""
FFmpeg-based sampler service for capturing frames and audio from live streams.
"""
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SampleMetadata(BaseModel):
    """Metadata for a captured sample."""
    snapshot_url: str
    audio_url: str
    timestamp: str
    source_url: str
    duration: Optional[float] = None
    confidence: Optional[float] = None


class SamplerService:
    """Service for sampling video streams with ffmpeg."""
    
    def __init__(self, output_dir: str = None):
        self.output_dir = Path(output_dir or settings.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Validate ffmpeg is available
        if not self._check_ffmpeg():
            raise RuntimeError("ffmpeg not found. Please install ffmpeg.")
    
    def _check_ffmpeg(self) -> bool:
        """Check if ffmpeg is available in PATH."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _generate_filenames(self, timestamp: datetime) -> tuple[str, str]:
        """Generate unique filenames for snapshot and audio files."""
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
        
        snapshot_name = f"snapshot_{timestamp_str}.jpg"
        audio_name = f"audio_{timestamp_str}.wav"
        
        return snapshot_name, audio_name
    
    def _capture_frame(self, source_url: str, output_path: str) -> bool:
        """Capture a single frame from the video stream."""
        try:
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output files
                "-i", source_url,
                "-frames:v", "1",  # Capture only 1 frame
                "-f", "image2",
                "-q:v", "2",  # High quality
                output_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"Frame capture failed: {result.stderr}")
                return False
            
            return os.path.exists(output_path) and os.path.getsize(output_path) > 0
            
        except subprocess.TimeoutExpired:
            logger.error("Frame capture timed out")
            return False
        except Exception as e:
            logger.error(f"Frame capture error: {e}")
            return False
    
    def _capture_audio(self, source_url: str, output_path: str, duration: int) -> bool:
        """Capture audio from the video stream."""
        try:
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output files
                "-i", source_url,
                "-t", str(duration),  # Duration in seconds
                "-vn",  # No video
                "-acodec", "pcm_s16le",  # PCM 16-bit little-endian
                "-ar", "44100",  # Sample rate
                "-ac", "2",  # Stereo
                output_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=duration + 10  # Add buffer time
            )
            
            if result.returncode != 0:
                logger.error(f"Audio capture failed: {result.stderr}")
                return False
            
            return os.path.exists(output_path) and os.path.getsize(output_path) > 0
            
        except subprocess.TimeoutExpired:
            logger.error("Audio capture timed out")
            return False
        except Exception as e:
            logger.error(f"Audio capture error: {e}")
            return False
    
    def capture_sample(self, source_url: str = None, duration: int = None) -> SampleMetadata:
        """
        Capture a single frame and audio sample from the source.
        
        Args:
            source_url: URL of the video stream (defaults to Cornell cam)
            duration: Audio duration in seconds (defaults to config)
            
        Returns:
            SampleMetadata with file paths and capture information
        """
        source_url = source_url or settings.cornell_cam_url
        duration = duration or settings.audio_duration
        
        timestamp = datetime.now()
        snapshot_name, audio_name = self._generate_filenames(timestamp)
        
        snapshot_path = self.output_dir / snapshot_name
        audio_path = self.output_dir / audio_name
        
        logger.info(f"Capturing sample from {source_url}")
        
        # Capture frame
        frame_success = self._capture_frame(source_url, str(snapshot_path))
        if not frame_success:
            raise RuntimeError("Failed to capture video frame")
        
        # Capture audio
        audio_success = self._capture_audio(source_url, str(audio_path), duration)
        if not audio_success:
            # Clean up snapshot if audio fails
            if snapshot_path.exists():
                snapshot_path.unlink()
            raise RuntimeError("Failed to capture audio")
        
        logger.info(f"Sample captured successfully: {snapshot_name}, {audio_name}")
        
        # Return metadata with local file paths
        # In a production system, these would be S3 URLs or similar
        return SampleMetadata(
            snapshot_url=str(snapshot_path.absolute()),
            audio_url=str(audio_path.absolute()),
            timestamp=timestamp.isoformat(),
            source_url=source_url,
            duration=float(duration)
        )


# Initialize the sampler service
sampler = SamplerService()

# FastAPI app
app = FastAPI(
    title="Birds with Friends - Ingest Service",
    description="Sampling service for capturing frames and audio from bird identification streams",
    version="0.1.0"
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "ingest-sampler",
        "timestamp": datetime.now().isoformat(),
        "ffmpeg_available": sampler._check_ffmpeg()
    }


@app.post("/dev/ingest/test-sample", response_model=SampleMetadata)
async def test_sample(source_url: Optional[str] = None, duration: Optional[int] = None):
    """
    Test endpoint to trigger a single capture and return metadata.
    
    Args:
        source_url: Optional custom source URL
        duration: Optional custom audio duration
    
    Returns:
        SampleMetadata with capture results
    """
    try:
        metadata = sampler.capture_sample(source_url=source_url, duration=duration)
        return metadata
    except Exception as e:
        logger.error(f"Sample capture failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Birds with Friends - Ingest Service",
        "version": "0.1.0",
        "description": "FFmpeg-based sampling service for bird identification streams",
        "endpoints": {
            "health": "/health",
            "test_sample": "/dev/ingest/test-sample"
        },
        "config": {
            "source_url": settings.cornell_cam_url,
            "sample_interval": settings.sample_interval,
            "audio_duration": settings.audio_duration,
            "output_dir": str(settings.output_dir)
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "ingest.sampler:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if settings.debug else "warning"
    )