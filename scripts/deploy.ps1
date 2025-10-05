# Birds with Friends - Production Deployment Helper

param(
    [Parameter(Position=0)]
    [string]$Command = "help",
    [Parameter(Position=1)]
    [string]$Environment = "production"
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

# Check prerequisites
function Test-Prerequisites {
    Write-Log "Checking deployment prerequisites..."
    
    # Check Docker
    try {
        $null = docker info 2>$null
        Write-Success "Docker is available"
    }
    catch {
        Write-Error-Custom "Docker is not running"
        return $false
    }
    
    # Check Docker Compose
    try {
        $null = docker-compose version 2>$null
        Write-Success "Docker Compose is available"
    }
    catch {
        Write-Error-Custom "Docker Compose is not available"
        return $false
    }
    
    # Check environment file
    if (Test-Path ".env") {
        Write-Success "Environment configuration found"
    } else {
        Write-Error-Custom "Missing .env file. Copy from .env.template and configure."
        return $false
    }
    
    return $true
}

# Validate environment configuration
function Test-Configuration {
    Write-Log "Validating environment configuration..."
    
    $required_vars = @(
        "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD",
        "REDIS_URL", "OPENAI_API_KEY", "CORS_ORIGINS"
    )
    
    $env_content = Get-Content ".env" -ErrorAction SilentlyContinue
    if (-not $env_content) {
        Write-Error-Custom "Could not read .env file"
        return $false
    }
    
    $missing_vars = @()
    foreach ($var in $required_vars) {
        if (-not ($env_content | Select-String -Pattern "^$var=")) {
            $missing_vars += $var
        }
    }
    
    if ($missing_vars.Count -gt 0) {
        Write-Error-Custom "Missing required environment variables: $($missing_vars -join ', ')"
        return $false
    }
    
    Write-Success "Environment configuration is valid"
    return $true
}

# Build production images
function Build-Images {
    Write-Log "Building production images..."
    
    # Build all services
    docker-compose -f docker-compose.full.yml build --no-cache
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Production images built successfully"
    } else {
        Write-Error-Custom "Failed to build production images"
        exit 1
    }
}

# Deploy production environment
function Start-Production {
    if (-not (Test-Prerequisites)) {
        exit 1
    }
    
    if (-not (Test-Configuration)) {
        exit 1
    }
    
    Write-Log "Starting production deployment..."
    
    # Create necessary directories
    $directories = @("data", "output", "story_data", "aggregator_data", "logs", "prometheus_data", "grafana_data")
    foreach ($dir in $directories) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
    }
    
    # Start production services
    docker-compose -f docker-compose.full.yml up -d
    
    # Wait for services to start
    Write-Log "Waiting for services to initialize..."
    Start-Sleep -Seconds 30
    
    # Check deployment health
    Test-DeploymentHealth
    
    Write-Success "Production deployment completed!"
    Write-Log "Application: https://your-domain.com"
    Write-Log "Grafana: https://your-domain.com/grafana"
}

# Stop production environment
function Stop-Production {
    Write-Log "Stopping production environment..."
    docker-compose -f docker-compose.full.yml down
    Write-Success "Production environment stopped"
}

# Update production deployment
function Update-Production {
    Write-Log "Updating production deployment..."
    
    # Pull latest images
    docker-compose -f docker-compose.full.yml pull
    
    # Rebuild custom images
    Build-Images
    
    # Restart services with zero downtime
    docker-compose -f docker-compose.full.yml up -d --force-recreate
    
    Write-Success "Production deployment updated"
}

# Check deployment health
function Test-DeploymentHealth {
    Write-Log "Checking deployment health..."
    
    $services = @("frontend", "api-gateway", "sampler", "audio-recognizer", "image-recognizer", "aggregator", "story-engine", "nginx", "postgres", "redis")
    
    foreach ($service in $services) {
        $status = docker-compose -f docker-compose.full.yml ps $service
        if ($status -match "Up") {
            Write-Success "$service is healthy"
        } else {
            Write-Warn "$service is not running"
        }
    }
    
    # Test API endpoints
    try {
        $response = Invoke-WebRequest -Uri "http://localhost/api/health" -TimeoutSec 5 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Success "API Gateway is responding"
        }
    }
    catch {
        Write-Warn "API Gateway is not responding"
    }
}

# View production logs
function Show-ProductionLogs {
    param([string]$ServiceName = "")
    
    if ($ServiceName) {
        docker-compose -f docker-compose.full.yml logs -f --tail=100 $ServiceName
    } else {
        docker-compose -f docker-compose.full.yml logs -f --tail=100
    }
}

# Backup production data
function Backup-Data {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backup_dir = "backups/$timestamp"
    
    Write-Log "Creating backup in $backup_dir..."
    
    New-Item -ItemType Directory -Path $backup_dir -Force | Out-Null
    
    # Backup database
    docker-compose -f docker-compose.full.yml exec -T postgres pg_dump -U birds_user birds_db > "$backup_dir/database.sql"
    
    # Backup data directories
    Copy-Item -Recurse "data" "$backup_dir/"
    Copy-Item -Recurse "story_data" "$backup_dir/"
    Copy-Item -Recurse "aggregator_data" "$backup_dir/"
    
    Write-Success "Backup created in $backup_dir"
}

# Scale services
function Set-Scale {
    param(
        [string]$Service,
        [int]$Replicas
    )
    
    Write-Log "Scaling $Service to $Replicas replicas..."
    docker-compose -f docker-compose.full.yml up -d --scale $Service=$Replicas
    Write-Success "Scaled $Service to $Replicas replicas"
}

# Show deployment status
function Show-Status {
    Write-Log "Production Deployment Status:"
    Write-Host ""
    
    # Service status
    docker-compose -f docker-compose.full.yml ps
    
    Write-Host ""
    Write-Log "Resource Usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
}

# Show help
function Show-Help {
    Write-Host "Birds with Friends - Production Deployment Helper" -ForegroundColor $Blue
    Write-Host ""
    Write-Host "Usage: .\scripts\deploy.ps1 [command] [options]"
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  check       Check deployment prerequisites and configuration"
    Write-Host "  build       Build production images"
    Write-Host "  deploy      Deploy production environment"
    Write-Host "  stop        Stop production environment"
    Write-Host "  update      Update production deployment"
    Write-Host "  health      Check deployment health"
    Write-Host "  logs        View production logs (add service name for specific service)"
    Write-Host "  backup      Backup production data"
    Write-Host "  scale       Scale service (usage: scale service_name replica_count)"
    Write-Host "  status      Show deployment status and resource usage"
    Write-Host "  help        Show this help message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\scripts\deploy.ps1 check"
    Write-Host "  .\scripts\deploy.ps1 deploy"
    Write-Host "  .\scripts\deploy.ps1 logs nginx"
    Write-Host "  .\scripts\deploy.ps1 scale audio-recognizer 3"
}

# Main command dispatcher
switch ($Command.ToLower()) {
    "check" { 
        $prereq = Test-Prerequisites
        $config = Test-Configuration
        if ($prereq -and $config) {
            Write-Success "All checks passed - ready for deployment"
        }
    }
    "build" { Build-Images }
    "deploy" { Start-Production }
    "stop" { Stop-Production }
    "update" { Update-Production }
    "health" { Test-DeploymentHealth }
    "logs" { Show-ProductionLogs -ServiceName $Environment }
    "backup" { Backup-Data }
    "scale" { 
        if ($args.Count -ge 2) {
            Set-Scale -Service $args[0] -Replicas $args[1]
        } else {
            Write-Error-Custom "Usage: scale service_name replica_count"
        }
    }
    "status" { Show-Status }
    default { Show-Help }
}