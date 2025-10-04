"""
Image Recognition Service API

FastAPI service for image-based bird recognition using WhosAtMyFeeder.
"""
import logging
from typing import Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Form

from ..shared.schemas import RecognitionEvent, RecognitionRequest
from ..shared.config import ImageRecognitionSettings
from .recognizer import ImageRecognizer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize settings and recognizer
settings = ImageRecognitionSettings()
recognizer = ImageRecognizer(settings)

# FastAPI app
app = FastAPI(
    title="Birds with Friends - Image Recognition Service",
    description="WhosAtMyFeeder adapter for image-based bird species recognition",
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
async def recognize_image(
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None)
):
    """
    Recognize bird species from image input.
    
    Args:
        file: Uploaded image file (JPG, PNG, BMP)
        url: URL to image file
        
    Returns:
        RecognitionEvent with detections, bounding boxes, and character instances
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
            source="image",
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
        "service": "Birds with Friends - Image Recognition Service",
        "version": "0.1.0",
        "description": "WhosAtMyFeeder adapter for image-based bird species recognition",
        "endpoints": {
            "health": "/health",
            "recognize": "/recognize"
        },
        "supported_formats": settings.allowed_image_types,
        "max_file_size": settings.max_file_size,
        "min_confidence": settings.min_confidence
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "recognition.image.service:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if settings.debug else "warning"
    )