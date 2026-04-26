# Launch Botnet Detection Dashboard System
Write-Host "Starting Botnet Detection System..." -ForegroundColor Cyan

# 1. Start Kafka
Write-Host "[1/4] Starting Kafka via Docker..." -ForegroundColor Yellow
docker compose up -d

# 2. Start Backend
Write-Host "[2/4] Starting FastAPI Backend..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "botnet_env\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000" -WindowStyle Normal

# 3. Start Consumer
Write-Host "[3/4] Starting Detection Consumer..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "botnet_env\Scripts\python.exe -m consumer.detection_consumer" -WindowStyle Normal

# 4. Start Frontend
Write-Host "[4/4] Starting React Dashboard..." -ForegroundColor Yellow
Set-Location dashboard/frontend-app
npm run dev
