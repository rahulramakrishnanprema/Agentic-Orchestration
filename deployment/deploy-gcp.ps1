# GCP Deployment Script for Aristotle-I (Two-Server Architecture)
# This script builds and deploys both Backend and Frontend to Google Cloud Run

param(
    [string]$ProjectId = "aristote-i",
    [string]$Region = "us-central1",
    [string]$BackendService = "aristotlei",
    [string]$FrontendService = "aristotlei-frontend",
    [string]$Repository = "aristotlei"
)

$ErrorActionPreference = "Stop"

Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host "  Aristotle-I Two-Server Deployment Script" -ForegroundColor Cyan
Write-Host "  Backend (Python) + Frontend (Nginx)" -ForegroundColor Cyan
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Verify Docker is running
Write-Host "[1/6] Checking Docker..." -ForegroundColor Yellow
try {
    docker info | Out-Null
    Write-Host "v Docker is running" -ForegroundColor Green
}
catch {
    Write-Host "x Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

# Step 2: Verify gcloud authentication
Write-Host "[2/6] Checking gcloud authentication..." -ForegroundColor Yellow
$currentProject = gcloud config get-value project 2>$null
if ($currentProject -ne $ProjectId) {
    Write-Host "x Current project is '$currentProject', expected '$ProjectId'" -ForegroundColor Red
    Write-Host "Setting project to $ProjectId..." -ForegroundColor Yellow
    gcloud config set project $ProjectId
}
Write-Host "v Authenticated to project: $ProjectId" -ForegroundColor Green

# Step 3: Configure Docker for Artifact Registry
Write-Host "[3/6] Configuring Docker for Artifact Registry..." -ForegroundColor Yellow
gcloud auth configure-docker "${Region}-docker.pkg.dev" --quiet
Write-Host "v Docker configured for Artifact Registry" -ForegroundColor Green

# Step 4: Build Backend Docker image
Write-Host "[4/10] Building Backend Docker image..." -ForegroundColor Yellow
$backendImageTag = "${Region}-docker.pkg.dev/${ProjectId}/${Repository}/${BackendService}:latest"
Write-Host "Backend image tag: $backendImageTag" -ForegroundColor Cyan

docker build -f deployment/Dockerfile -t $backendImageTag .

if ($LASTEXITCODE -ne 0) {
    Write-Host "x Backend Docker build failed." -ForegroundColor Red
    exit 1
}
Write-Host "v Backend image built successfully" -ForegroundColor Green

# Step 5: Push Backend image to Artifact Registry
Write-Host "[5/10] Pushing Backend image to Artifact Registry..." -ForegroundColor Yellow
docker push $backendImageTag

if ($LASTEXITCODE -ne 0) {
    Write-Host "x Backend push failed" -ForegroundColor Red
    exit 1
}
Write-Host "v Backend image pushed" -ForegroundColor Green

# Step 6: Deploy Backend to Cloud Run
Write-Host "[6/10] Deploying Backend to Cloud Run..." -ForegroundColor Yellow
gcloud run services replace deployment/cloudrun-service.yaml --region=$Region

if ($LASTEXITCODE -ne 0) {
    Write-Host "x Backend deployment failed" -ForegroundColor Red
    exit 1
}
Write-Host "v Backend deployed successfully" -ForegroundColor Green

# Step 7: Build Frontend Docker image (Nginx)
Write-Host "[7/10] Building Frontend Docker image (Nginx)..." -ForegroundColor Yellow
$frontendImageTag = "${Region}-docker.pkg.dev/${ProjectId}/${Repository}/${FrontendService}:latest"
Write-Host "Frontend image tag: $frontendImageTag" -ForegroundColor Cyan

docker build -f deployment/Dockerfile.frontend -t $frontendImageTag .

if ($LASTEXITCODE -ne 0) {
    Write-Host "x Frontend Docker build failed." -ForegroundColor Red
    exit 1
}
Write-Host "v Frontend image built successfully" -ForegroundColor Green

# Step 8: Push Frontend image to Artifact Registry
Write-Host "[8/10] Pushing Frontend image to Artifact Registry..." -ForegroundColor Yellow
docker push $frontendImageTag

if ($LASTEXITCODE -ne 0) {
    Write-Host "x Frontend push failed" -ForegroundColor Red
    exit 1
}
Write-Host "v Frontend image pushed" -ForegroundColor Green

# Step 9: Deploy Frontend to Cloud Run
Write-Host "[9/10] Deploying Frontend to Cloud Run..." -ForegroundColor Yellow
gcloud run deploy $FrontendService `
    --image=$frontendImageTag `
    --platform=managed `
    --region=$Region `
    --port=8080 `
    --memory=512Mi `
    --cpu=1 `
    --timeout=300 `
    --allow-unauthenticated

if ($LASTEXITCODE -ne 0) {
    Write-Host "x Frontend deployment failed" -ForegroundColor Red
    exit 1
}
Write-Host "v Frontend deployed successfully" -ForegroundColor Green

# Step 10: Get service URLs
Write-Host "[10/10] Retrieving service URLs..." -ForegroundColor Yellow
$backendUrl = gcloud run services describe $BackendService --region=$Region --format='value(status.url)' 2>$null
$frontendUrl = gcloud run services describe $FrontendService --region=$Region --format='value(status.url)' 2>$null

Write-Host ""
Write-Host "===========================================================" -ForegroundColor Green
Write-Host "  v Deployment Successful!" -ForegroundColor Green
Write-Host "  Two-Server Architecture Deployed" -ForegroundColor Green
Write-Host "===========================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Backend API URL:  " -ForegroundColor Cyan -NoNewline
Write-Host $backendUrl -ForegroundColor White
Write-Host "Frontend UI URL:  " -ForegroundColor Cyan -NoNewline
Write-Host $frontendUrl -ForegroundColor White
Write-Host ""
Write-Host "Access your application at: $frontendUrl" -ForegroundColor Yellow
Write-Host ""
Write-Host "Services deployed:" -ForegroundColor Cyan
Write-Host "  1. Backend (Python):  $BackendService" -ForegroundColor White
Write-Host "  2. Frontend (Nginx):  $FrontendService" -ForegroundColor White
Write-Host ""

