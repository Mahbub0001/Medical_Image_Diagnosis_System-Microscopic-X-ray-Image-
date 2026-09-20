# ─────────────────────────────────────────────────────────────────
# BioLens — Docker Hub Push Script
# Usage: .\dockerhub_push.ps1 -Username mahbub0001
# ─────────────────────────────────────────────────────────────────
param(
    [Parameter(Mandatory=$true)]
    [string]$Username,

    [string]$Tag = "latest"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  BioLens — Docker Hub Push" -ForegroundColor Cyan
Write-Host "  Username : $Username" -ForegroundColor Cyan
Write-Host "  Tag      : $Tag" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# ── Login ──────────────────────────────────────────────────────
Write-Host "[1/6] Logging in to Docker Hub..." -ForegroundColor Yellow
docker login
if ($LASTEXITCODE -ne 0) { Write-Error "Docker login failed."; exit 1 }

# ── Backend ────────────────────────────────────────────────────
Write-Host ""
Write-Host "[2/6] Building backend image..." -ForegroundColor Yellow
docker build -t "${Username}/biolens-backend:${Tag}" ./backend
if ($LASTEXITCODE -ne 0) { Write-Error "Backend build failed."; exit 1 }

Write-Host "[3/6] Pushing backend image..." -ForegroundColor Yellow
docker push "${Username}/biolens-backend:${Tag}"
if ($LASTEXITCODE -ne 0) { Write-Error "Backend push failed."; exit 1 }
Write-Host "  Backend pushed: ${Username}/biolens-backend:${Tag}" -ForegroundColor Green

# ── Frontend ───────────────────────────────────────────────────
Write-Host ""
Write-Host "[4/6] Building frontend image..." -ForegroundColor Yellow
docker build -t "${Username}/biolens-frontend:${Tag}" ./frontend
if ($LASTEXITCODE -ne 0) { Write-Error "Frontend build failed."; exit 1 }

Write-Host "[5/6] Pushing frontend image..." -ForegroundColor Yellow
docker push "${Username}/biolens-frontend:${Tag}"
if ($LASTEXITCODE -ne 0) { Write-Error "Frontend push failed."; exit 1 }
Write-Host "  Frontend pushed: ${Username}/biolens-frontend:${Tag}" -ForegroundColor Green

# ── Summary ────────────────────────────────────────────────────
Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "  Successfully pushed to Docker Hub!" -ForegroundColor Green
Write-Host ""
Write-Host "  Backend  : https://hub.docker.com/r/${Username}/biolens-backend"
Write-Host "  Frontend : https://hub.docker.com/r/${Username}/biolens-frontend"
Write-Host ""
Write-Host "  Pull commands:" -ForegroundColor Cyan
Write-Host "  docker pull ${Username}/biolens-backend:${Tag}"
Write-Host "  docker pull ${Username}/biolens-frontend:${Tag}"
Write-Host "==========================================" -ForegroundColor Green
