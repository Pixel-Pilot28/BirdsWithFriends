"""
Audio Recognition Service API

FastAPI service for audio-based bird recognition using BirdCAGE.
"""
import logging
from typing import Optional, Union
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse

from ..shared.schemas import RecognitionEvent, RecognitionRequest
from ..shared.config import AudioRecognitionSettings
from .recognizer import AudioRecognizer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize settings and recognizer
settings = AudioRecognitionSettings()
recognizer = AudioRecognizer(settings)

# FastAPI app
app = FastAPI(
    title="Birds with Friends - Audio Recognition Service",
    description="BirdCAGE adapter for audio-based bird species recognition",
    version="0.1.0"
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": "0.1.0",
        "model_loaded": True,  # In real implementation, check if model is loaded
        "min_confidence": settings.min_confidence
    }


@app.post("/recognize", response_model=RecognitionEvent)
async def recognize_audio(
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None)
):
    """
    Recognize bird species from audio input.
    
    Args:
        file: Uploaded audio file (WAV, MP3, M4A, FLAC)
        url: URL to audio file
        
    Returns:
        RecognitionEvent with detections and character instances
    """
    try:
        # Validate input
        if not file and not url:
            raise HTTPException(
                status_code=400, 
                detail="Either file or url parameter is required"
            )
        
        if file and url:
            raise HTTPException(
                status_code=400,
                detail="Provide either file or url, not both"
            )
        
        detections = []
        snapshot_url = None
        
        if file:
            # Validate file size
            if file.size > settings.max_file_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size: {settings.max_file_size} bytes"
                )
            
            # Process uploaded file
            detections = await recognizer.recognize_from_file(file.file, file.filename)
            snapshot_url = f"uploaded://{file.filename}"
            
        elif url:
            # Process URL
            detections = await recognizer.recognize_from_url(url)
            snapshot_url = url
        
        # Create unified event
        event = recognizer.create_event(
            detections=detections,
            source="audio",
            snapshot_url=snapshot_url
        )
        
        logger.info(f"Recognition complete: {len(detections)} detections, {len(event.characters)} characters")
        
        return event
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"Recognition failed: {e}")
        raise HTTPException(status_code=500, detail="Recognition processing failed")


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Birds with Friends - Audio Recognition Service",
        "version": "0.1.0",
        "description": "BirdCAGE adapter for audio-based bird species recognition",
        "endpoints": {
            "health": "/health",
            "recognize": "/recognize"
        },
        "supported_formats": settings.allowed_audio_types,
        "max_file_size": settings.max_file_size,
        "min_confidence": settings.min_confidence
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "recognition.audio.service:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if settings.debug else "warning"
    )