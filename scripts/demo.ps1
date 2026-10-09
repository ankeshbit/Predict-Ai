# scripts/demo.ps1 — Reviewer Localhost All-in-One Launcher
# Starts local Postgres, executes migrations, seeds default accounts and models,
# and starts backend and frontend development servers.
# Never prints secrets or passwords.

param (
    [switch]$SkipServers,
    [switch]$Reset
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Predict-Ai (PrediCore) — Reviewer Localhost Environment" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Environment Setup
$EnvFile = Join-Path $PSScriptRoot "..\.env"
$BackendEnvFile = Join-Path $PSScriptRoot "..\backend\.env"

if (-not (Test-Path $EnvFile)) {
    Write-Host "[*] Creating .env from .env.example with local PostgreSQL configuration..." -ForegroundColor Yellow
    $ExampleContent = Get-Content (Join-Path $PSScriptRoot "..\.env.example") -Raw
    $LocalEnv = $ExampleContent `
        -replace "DATABASE_URL=.*", "DATABASE_URL=postgresql+psycopg://postgres:postgrespassword@localhost:5432/predict_ai" `
        -replace "DATABASE_URL_DIRECT=.*", "DATABASE_URL_DIRECT=postgresql+psycopg://postgres:postgrespassword@localhost:5432/predict_ai" `
        -replace "TEST_DATABASE_URL=.*", "TEST_DATABASE_URL=postgresql+psycopg://postgres:postgrespassword@localhost:5432/predict_ai_test" `
        -replace "INITIAL_ADMIN_PASSWORD=.*", "INITIAL_ADMIN_PASSWORD=AdminReviewer2026#Secure" `
        -replace "INITIAL_ENGINEER_PASSWORD=.*", "INITIAL_ENGINEER_PASSWORD=Engineer2026#Secure" `
        -replace "SECRET_KEY=.*", "SECRET_KEY=dev_secret_key_0123456789abcdef0123456789abcdef"
    Set-Content -Path $EnvFile -Value $LocalEnv
}

if (-not (Test-Path $BackendEnvFile)) {
    Copy-Item $EnvFile $BackendEnvFile
}

# Load environment variables into current PowerShell session (without printing)
Get-Content $EnvFile | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
        $parts = $line.Split("=", 2)
        [System.Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
    }
}

# 2. Local PostgreSQL via Docker Compose
Write-Host "[*] Starting local PostgreSQL container..." -ForegroundColor Cyan
docker compose up -d test-postgres

# Wait for Postgres container to become healthy
Write-Host "[*] Waiting for PostgreSQL readiness..." -ForegroundColor Cyan
$retries = 30
$ready = $false
while ($retries -gt 0 -and -not $ready) {
    $status = docker inspect --format="{{.State.Health.Status}}" predict_ai_test_postgres 2>$null
    if ($status -eq "healthy") {
        $ready = $true
        break
    }
    Start-Sleep -Seconds 1
    $retries--
}

if (-not $ready) {
    Write-Host "[-] Error: Local PostgreSQL container failed to report healthy status within 30s." -ForegroundColor Red
    exit 1
}
Write-Host "[+] Local PostgreSQL is healthy on port 5432." -ForegroundColor Green

# 3. Database Migrations
Write-Host "[*] Running Alembic database migrations..." -ForegroundColor Cyan
Push-Location (Join-Path $PSScriptRoot "..\backend")
try {
    python -m alembic upgrade head
} finally {
    Pop-Location
}
Write-Host "[+] Database migrations up to date." -ForegroundColor Green

# 4. Seed Default Accounts & Settings
Write-Host "[*] Seeding default accounts and health band configuration..." -ForegroundColor Cyan
Push-Location (Join-Path $PSScriptRoot "..\backend")
try {
    python -m app.cli seed-defaults
} finally {
    Pop-Location
}

# 5. Register Model Bundle
$BundlePath = "model_artifacts/cmapss-fd001-h30-20261001T203719Z"
Write-Host "[*] Registering offline model bundle ($BundlePath)..." -ForegroundColor Cyan
Push-Location (Join-Path $PSScriptRoot "..\backend")
try {
    python -m app.cli register-model --bundle-path $BundlePath --activate
} finally {
    Pop-Location
}

# 6. Seed Demo Fleet
Write-Host "[*] Seeding demo fleet machines (Healthy, Warning, Critical held-out engines)..." -ForegroundColor Cyan
Push-Location (Join-Path $PSScriptRoot "..\backend")
try {
    python -m app.cli seed-demo --bundle-path $BundlePath
} finally {
    Pop-Location
}

if ($SkipServers) {
    Write-Host "[+] Demo environment setup complete (servers skipped)." -ForegroundColor Green
    exit 0
}

# 7. Launch Servers
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "[+] Reviewer setup complete! Starting backend and frontend..." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Frontend:  http://localhost:5173" -ForegroundColor White
Write-Host "  Backend:   http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs:  http://localhost:8000/docs" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Reviewer login credentials configured in .env" -ForegroundColor Gray
Write-Host "See docs/REVIEWER_GUIDE.md for a 5-minute evaluation walkthrough." -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor Cyan

# Start backend in a separate job/process
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; python -m uvicorn app.main:app --port 8000 --reload"
# Start frontend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"
