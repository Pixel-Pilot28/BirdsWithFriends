#!/bin/bash

# Makefile alternative for cross-platform development
# Usage: ./scripts/dev.sh [command]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

success() {
    echo -e "${GREEN}✓ $1${NC}"
}

warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
}

# Setup development environment
setup() {
    log "Setting up development environment..."
    
    # Create .env files if they don't exist
    if [ ! -f .env.development ]; then
        log "Creating .env.development from template..."
        cp .env.template .env.development
        success "Created .env.development"
    fi
    
    if [ ! -f .env ]; then
        log "Creating .env from development template..."
        cp .env.development .env
        success "Created .env"
    fi
    
    # Create necessary directories
    mkdir -p data output story_data aggregator_data logs
    success "Created required directories"
    
    # Build development images
    log "Building development images..."
    docker-compose -f docker-compose.dev.yml build
    success "Development images built"
}

# Start development environment
start() {
    check_docker
    log "Starting development environment..."
    docker-compose -f docker-compose.dev.yml up -d
    
    # Wait for services to be ready
    log "Waiting for services to be ready..."
    sleep 10
    
    # Check service health
    check_health
    
    success "Development environment started!"
    log "Frontend: http://localhost:3000"
    log "API Gateway: http://localhost:8001"
    log "PgAdmin: http://localhost:5050"
    log "Redis Commander: http://localhost:8081"
}

# Stop development environment
stop() {
    log "Stopping development environment..."
    docker-compose -f docker-compose.dev.yml down
    success "Development environment stopped"
}

# Restart development environment
restart() {
    log "Restarting development environment..."
    stop
    start
}

# View logs
logs() {
    service=${2:-""}
    if [ -n "$service" ]; then
        docker-compose -f docker-compose.dev.yml logs -f "$service"
    else
        docker-compose -f docker-compose.dev.yml logs -f
    fi
}

# Check service health
check_health() {
    log "Checking service health..."
    
    services=("frontend" "api-gateway" "sampler" "audio-recognizer" "image-recognizer" "aggregator" "story-engine")
    
    for service in "${services[@]}"; do
        if docker-compose -f docker-compose.dev.yml ps "$service" | grep -q "Up"; then
            success "$service is running"
        else
            warn "$service is not running"
        fi
    done
}

# Run tests
test() {
    log "Running tests..."
    docker-compose -f docker-compose.dev.yml exec backend python -m pytest tests/ -v
    success "Tests completed"
}

# Clean up development environment
clean() {
    log "Cleaning up development environment..."
    docker-compose -f docker-compose.dev.yml down -v --remove-orphans
    docker system prune -f
    success "Development environment cleaned"
}

# Install Python dependencies
install_deps() {
    log "Installing Python dependencies..."
    docker-compose -f docker-compose.dev.yml exec backend pip install -r requirements.txt
    success "Dependencies installed"
}

# Run database migrations
migrate() {
    log "Running database migrations..."
    # Add migration commands here when implemented
    success "Database migrations completed"
}

# Show help
help() {
    echo -e "${BLUE}Birds with Friends - Development Helper${NC}"
    echo ""
    echo "Usage: ./scripts/dev.sh [command]"
    echo ""
    echo "Commands:"
    echo "  setup       Setup development environment"
    echo "  start       Start development services"
    echo "  stop        Stop development services"
    echo "  restart     Restart development services"
    echo "  logs        View logs (add service name to view specific service)"
    echo "  health      Check service health"
    echo "  test        Run tests"
    echo "  clean       Clean up containers and volumes"
    echo "  deps        Install Python dependencies"
    echo "  migrate     Run database migrations"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./scripts/dev.sh setup"
    echo "  ./scripts/dev.sh start"
    echo "  ./scripts/dev.sh logs sampler"
    echo "  ./scripts/dev.sh test"
}

# Main command dispatcher
case "${1:-help}" in
    setup)
        setup
        ;;
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    logs)
        logs "$@"
        ;;
    health)
        check_health
        ;;
    test)
        test
        ;;
    clean)
        clean
        ;;
    deps)
        install_deps
        ;;
    migrate)
        migrate
        ;;
    help|*)
        help
        ;;
esac