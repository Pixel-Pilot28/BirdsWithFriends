<img src="https://github.com/Pixel-Pilot28/BirdsWithFriends/blob/main/Icons/file_00000000d0f861f99b5efbebd9d61d8c.png" width="200" />

# Birds with Friends

A real-time bird identification and storytelling app that ingests audio/video/image detections from existing bird-identification projects, converts species + counts + user attributes into structured story prompts, generates stories with an LLM, and presents them in a web UI.

## Architecture Overview

### Components

- **Ingest service** — pulls live stream, extracts audio frames & video frames (ffmpeg), forwards to recognizers
- **Recognition layer** — uses BirdCAGE for audio identification and WhosAtMyFeeder for image/video inference  
- **Event stream / broker** — lightweight message queue (MQTT or Redis stream) that publishes recognition events
- **Story engine** — receives events, aggregates over time windows and generates story chunks using LLM
- **API / backend** — FastAPI service to serve UI and manage story generation
- **Web UI** — React app to show live feed, snapshots, story timeline, user controls
- **Storage** — PostgreSQL for metadata; S3/minio for snapshots; Redis for caching

## Current Status

### Feature 1 — Ingest & Sampling (MVP)

 Docker containerization
 Health endpoints
 Sample capture API

### Feature 2 — Recognition Services

 Audio recognition adapter (BirdCAGE mock)
 Image recognition adapter (WhosAtMyFeeder mock)  
 Unified event schema
 Multi-count character generation
 Confidence threshold handling
 Docker services integration

### Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Run sampler service (method 1)
python run_dev.py

# Or run directly (method 2)
python -m ingest.sampler

# Test the service
python test_sampler.py
```

### Docker (Recommended)

```bash
# Build and run all services
docker-compose up

# Run specific services
docker-compose up -d sampler audio-recognizer image-recognizer

# View logs
docker-compose logs -f sampler

# Test recognition services
python verify_recognition.py
```

### API Endpoints

**Ingest Service** (http://localhost:8001):
- `GET /` - Service information and configuration
- `GET /health` - Health check endpoint
- `POST /dev/ingest/test-sample` - Trigger a test sample capture

**Audio Recognition** (http://localhost:8002):
- `GET /health` - Health check endpoint
- `POST /recognize` - Recognize birds from audio (file upload or URL)

**Image Recognition** (http://localhost:8003):
- `GET /health` - Health check endpoint  
- `POST /recognize` - Recognize birds from images (file upload or URL)

Example usage:
```bash
# Test sample capture
curl -X POST "http://localhost:8001/dev/ingest/test-sample?duration=3"

# Audio recognition
curl -X POST http://localhost:8002/recognize -d "url=http://example.com/birds.wav"

# Image recognition  
curl -X POST http://localhost:8003/recognize -F "file=@bird_photo.jpg"
```

## Environment Configuration

Copy `.env.example` to `.env` and configure:

- `CORNELL_CAM_URL` - Cornell Lab YouTube live stream URL
- `SAMPLE_INTERVAL` - Capture interval in seconds (default: 10)
- `AUDIO_DURATION` - Audio clip duration in seconds (default: 5)
- `OUTPUT_DIR` - Local output directory for samples
