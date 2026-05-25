#Requires -Version 5.1
param(
    [switch]$SkipIngest,
    [switch]$SkipSolver,
    [switch]$Local
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$GatewayDir = Join-Path $RepoRoot "layer2_3_gateway"
$SolverDir = Join-Path $RepoRoot "fleet-route-optimizer-cvrptw"
$SolverDockerDir = Join-Path $SolverDir "docker"
$TravelEnv = Join-Path $GatewayDir "travel.env"

function Import-TravelEnv {
    Get-Content $TravelEnv | ForEach-Object {
        if ($_ -match '^\s*([^#=]+?)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            Set-Item -Path "env:$name" -Value $value
        }
    }
    # Local processes talk to Postgres/Solver on host, not Docker service names.
    $env:SQL_HOST = "127.0.0.1"
    $env:LAYER4_BASE_URL = "http://127.0.0.1:8000"
}

function Wait-HttpOk {
    param(
        [string]$Url,
        [string]$Label,
        [int]$MaxSec = 120,
        [switch]$RejectMockGateway
    )
    $deadline = (Get-Date).AddSeconds($MaxSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($r.StatusCode -eq 200) {
                if ($RejectMockGateway -and $r.Content -match "Mock Gateway") {
                    Write-Host "WARN: $Label responded but is Mock Gateway - waiting for real stack..."
                } else {
                    Write-Host "OK: $Label"
                    return
                }
            }
        } catch {}
        Start-Sleep -Seconds 3
    }
    throw "Timeout waiting for $Label at $Url"
}

function Wait-PostgresReady {
    param([int]$MaxSec = 90)
    $deadline = (Get-Date).AddSeconds($MaxSec)
    Push-Location $GatewayDir
    try {
        while ((Get-Date) -lt $deadline) {
            docker compose exec -T db pg_isready -d travel -U travel 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "OK: PostgreSQL"
                return
            }
            Start-Sleep -Seconds 3
        }
        throw "Timeout waiting for PostgreSQL"
    } finally {
        Pop-Location
    }
}

function Stop-PortListener {
    param([int]$Port)
    Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique |
        ForEach-Object {
            $proc = Get-Process -Id $_ -ErrorAction SilentlyContinue
            if ($proc) {
                Write-Host "Stopping $($proc.ProcessName) (PID $_) on port $Port"
                Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
            }
        }
}

function Install-GatewayDeps {
    Write-Host "Installing Gateway Python deps (pip)..."
    python -m pip install -q `
        "fastapi>=0.114" "uvicorn>=0.30" "sqlalchemy>=2.0" "pydantic-settings>=2.5" `
        "httpx>=0.27" "psycopg[binary,pool]>=3.2" "alembic>=1.13" "geoalchemy2>=0.15" `
        "geojson-pydantic>=1.1" "pgvector>=0.3" "openai>=1.50" "instructor>=1.4" `
        "slowapi>=0.1" "gunicorn>=22" "python-dotenv>=1.0"
}

function Install-SolverDeps {
    Write-Host "Installing Solver Python deps (pip)..."
    python -m pip install -q -r (Join-Path $SolverDir "requirements.txt")
}

Write-Host "=== Full-stack bootstrap (Local=$Local) ==="

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker not found. Install Docker Desktop."
}
if (-not (Test-Path $TravelEnv)) {
    throw "Missing travel.env. Copy layer2_3_gateway/travel.env.example -> travel.env and add LLM key."
}

Stop-PortListener -Port 8001
Stop-PortListener -Port 8000

Push-Location $GatewayDir
try {
    Write-Host "Starting PostgreSQL..."
    docker compose up -d db
    Wait-PostgresReady

    if ($Local) {
        Import-TravelEnv
        Install-GatewayDeps

        Write-Host "Running migrations (local Python)..."
        python -m alembic upgrade head

        if (-not $SkipIngest) {
            Write-Host "Ingesting Hue POIs (local Python)..."
            python -m ingestion.ingest_pois --csv ingestion/sample_data/hue_pois.csv --skip-embeddings
        }

        Write-Host "Starting Gateway (local Python, port 8001)..."
        Start-Process -FilePath "python" -ArgumentList "run_gateway.py" -WorkingDirectory $GatewayDir -WindowStyle Hidden
        Wait-HttpOk "http://localhost:8001/v1/trip/health" "Gateway health" 120 -RejectMockGateway
    } else {
        Write-Host "Running migrations (Docker - requires poetry.lock)..."
        docker compose run --rm app alembic upgrade head

        if (-not $SkipIngest) {
            Write-Host "Ingesting Hue POIs (Docker)..."
            docker compose run --rm app python -m ingestion.ingest_pois `
                --csv ingestion/sample_data/hue_pois.csv --skip-embeddings
        }

        Write-Host "Starting Gateway (Docker)..."
        docker compose up -d app
        Wait-HttpOk "http://localhost:8001/v1/trip/health" "Gateway health" 120 -RejectMockGateway
    }
} finally {
    Pop-Location
}

if (-not $SkipSolver) {
    Push-Location $SolverDockerDir
    try {
        Write-Host "Starting OSRM..."
        docker compose up -d osrm-hue
    } finally {
        Pop-Location
    }

    if ($Local) {
        Install-SolverDeps
        Write-Host "Starting Solver (local Python, port 8000)..."
        Start-Process -FilePath "python" -ArgumentList "-m", "src.app" -WorkingDirectory $SolverDir -WindowStyle Hidden
    } else {
        Write-Host "Starting Solver (Docker - requires wheels/)..."
        docker compose up -d backend
    }
    Wait-HttpOk "http://localhost:8000/health" "Solver health" 180
}

Write-Host "=== Bootstrap complete ==="
Write-Host "Gateway: http://localhost:8001/v1/trip/health"
Write-Host "Solver:  http://localhost:8000/health"
Write-Host "Next: cd fleet-route-optimizer-cvrptw/webui; npm run test:e2e:live"
