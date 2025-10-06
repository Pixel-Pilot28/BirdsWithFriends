# Dockerfile for Birds with Friends - Story Engine Service
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory for story database
RUN mkdir -p story_data

# Set Python path to include current directory
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8005

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8005/health || exit 1

# Run the story engine service
CMD ["python", "-m", "uvicorn", "story_engine.service:app", "--host", "0.0.0.0", "--port", "8005"]