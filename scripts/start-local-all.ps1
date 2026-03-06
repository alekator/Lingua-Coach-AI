param(
  [switch]$SkipDocker
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$webDir = Join-Path $root "web"
$desktopDir = Join-Path $root "desktop"

Write-Host "== LinguaCoach Local One-Command Start ==" -ForegroundColor Cyan

if (-not $SkipDocker) {
  Write-Host "Starting backend stack (API + ASR + TTS + Postgres) in local-model mode..." -ForegroundColor Yellow
  Push-Location $root
  try {
    docker compose -f docker-compose.yml -f docker-compose.local-models.yml up -d --build
  } finally {
    Pop-Location
  }
}

Write-Host "Starting web dev server..." -ForegroundColor Yellow
Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "cd '$webDir'; npm run dev"

Start-Sleep -Seconds 2

Write-Host "Starting desktop shell..." -ForegroundColor Yellow
Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "cd '$desktopDir'; npm run start:web"

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host "Web: http://localhost:5173"
Write-Host "API: http://localhost:8000/health"
Write-Host ""
Write-Host "To stop backend containers later:"
Write-Host "docker compose -f docker-compose.yml -f docker-compose.local-models.yml down"
