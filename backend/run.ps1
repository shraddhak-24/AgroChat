# AgroChat Backend Startup Script (Windows PowerShell)

Write-Host "AgroChat Backend Launcher" -ForegroundColor Green
$line = New-Object System.String('=',60)
Write-Host $line -ForegroundColor Green

# Check if Python is installed
Write-Host "✓ Checking Python installation..." -ForegroundColor Cyan
python --version | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Python not found. Please install Python 3.9+ first." -ForegroundColor Red
    exit 1
}

# Install/upgrade dependencies
Write-Host "✓ Installing dependencies..." -ForegroundColor Cyan
pip install -r requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Host "Some dependencies failed to install. Continuing anyway..." -ForegroundColor Yellow
}

# Launch backend
Write-Host "✓ Starting FastAPI server..." -ForegroundColor Cyan
Write-Host "Starting FastAPI server..." -ForegroundColor Cyan
Write-Host "API URL: http://127.0.0.1:8005" -ForegroundColor Green
Write-Host "API Docs: http://127.0.0.1:8005/docs" -ForegroundColor Green
Write-Host $line -ForegroundColor Green
Write-Host ""

# Ensure Python prints unicode correctly
$env:PYTHONIOENCODING = "utf-8"

python app.py
