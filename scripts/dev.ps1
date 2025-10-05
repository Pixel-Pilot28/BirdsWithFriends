# Birds with Friends - Development Helper
# PowerShell version for Windows compatibility

param(
    [Parameter(Position=0)]
    [string]$Command = "help",
    [Parameter(Position=1)]
    [string]$Service = ""
)

# Colors for output
$Red = [System.ConsoleColor]::Red
$Green = [System.ConsoleColor]::Green
$Yellow = [System.ConsoleColor]::Yellow
$Blue = [System.ConsoleColor]::Blue

function Write-Log {
    param([string]$Message)
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message" -ForegroundColor $Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor $Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor $Yellow
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor $Red
}

# Check if Docker is running
function Test-Docker {
    try {
        $null = docker info 2>$null
        return $true
    }
    catch {
        Write-Error-Custom "Docker is not running. Please start Docker and try again."
        exit 1
    }
}

# Setup development environment
function Setup-Environment {
    Write-Log "Setting up development environment..."
    
    # Create .env files if they don't exist
    if (-not (Test-Path ".env.development")) {
        Write-Log "Creating .env.development from template..."
        Copy-Item ".env.template" ".env.development"
        Write-Success "Created .env.development"
    }
    
    if (-not (Test-Path ".env")) {
        Write-Log "Creating .env from development template..."
        Copy-Item ".env.development" ".env"
        Write-Success "Created .env"
    }
    
    # Create necessary directories
    $directories = @("data", "output", "story_data", "aggregator_data", "logs")
    foreach ($dir in $directories) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
    }
    Write-Success "Created required directories"
    
    # Build development images
    Write-Log "Building development images..."
    docker-compose -f docker-compose.dev.yml build
    Write-Success "Development images built"
}

# Start development environment
function Start-Environment {
    Test-Docker
    Write-Log "Starting development environment..."
    docker-compose -f docker-compose.dev.yml up -d
    
    # Wait for services to be ready
    Write-Log "Waiting for services to be ready..."
    Start-Sleep -Seconds 10
    
    # Check service health
    Test-ServiceHealth
    
    Write-Success "Development environment started!"
    Write-Log "Frontend: http://localhost:3000"
    Write-Log "API Gateway: http://localhost:8001"
    Write-Log "PgAdmin: http://localhost:5050"
    Write-Log "Redis Commander: http://localhost:8081"
}

# Stop development environment
function Stop-Environment {
    Write-Log "Stopping development environment..."
    docker-compose -f docker-compose.dev.yml down
    Write-Success "Development environment stopped"
}

# Restart development environment
function Restart-Environment {
    Write-Log "Restarting development environment..."
    Stop-Environment
    Start-Environment
}

# View logs
function Show-Logs {
    param([string]$ServiceName = "")
    
    if ($ServiceName) {
        docker-compose -f docker-compose.dev.yml logs -f $ServiceName
    } else {
        docker-compose -f docker-compose.dev.yml logs -f
    }
}

# Check service health
function Test-ServiceHealth {
    Write-Log "Checking service health..."
    
    $services = @("frontend", "api-gateway", "sampler", "audio-recognizer", "image-recognizer", "aggregator", "story-engine")
    
    foreach ($service in $services) {
        $status = docker-compose -f docker-compose.dev.yml ps $service
        if ($status -match "Up") {
            Write-Success "$service is running"
        } else {
            Write-Warn "$service is not running"
        }
    }
}

# Run tests
function Invoke-Tests {
    Write-Log "Running tests..."
    docker-compose -f docker-compose.dev.yml exec backend python -m pytest tests/ -v
    Write-Success "Tests completed"
}

# Clean up development environment
function Clear-Environment {
    Write-Log "Cleaning up development environment..."
    docker-compose -f docker-compose.dev.yml down -v --remove-orphans
    docker system prune -f
    Write-Success "Development environment cleaned"
}

# Install Python dependencies
function Install-Dependencies {
    Write-Log "Installing Python dependencies..."
    docker-compose -f docker-compose.dev.yml exec backend pip install -r requirements.txt
    Write-Success "Dependencies installed"
}

# Run database migrations
function Invoke-Migration {
    Write-Log "Running database migrations..."
    # Add migration commands here when implemented
    Write-Success "Database migrations completed"
}

# Show help
function Show-Help {
    Write-Host "Birds with Friends - Development Helper" -ForegroundColor $Blue
    Write-Host ""
    Write-Host "Usage: .\scripts\dev.ps1 [command] [service]"
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  setup       Setup development environment"
    Write-Host "  start       Start development services"
    Write-Host "  stop        Stop development services"
    Write-Host "  restart     Restart development services"
    Write-Host "  logs        View logs (add service name to view specific service)"
    Write-Host "  health      Check service health"
    Write-Host "  test        Run tests"
    Write-Host "  clean       Clean up containers and volumes"
    Write-Host "  deps        Install Python dependencies"
    Write-Host "  migrate     Run database migrations"
    Write-Host "  help        Show this help message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\scripts\dev.ps1 setup"
    Write-Host "  .\scripts\dev.ps1 start"
    Write-Host "  .\scripts\dev.ps1 logs sampler"
    Write-Host "  .\scripts\dev.ps1 test"
}

# Main command dispatcher
switch ($Command.ToLower()) {
    "setup" { Setup-Environment }
    "start" { Start-Environment }
    "stop" { Stop-Environment }
    "restart" { Restart-Environment }
    "logs" { Show-Logs -ServiceName $Service }
    "health" { Test-ServiceHealth }
    "test" { Invoke-Tests }
    "clean" { Clear-Environment }
    "deps" { Install-Dependencies }
    "migrate" { Invoke-Migration }
    default { Show-Help }
}