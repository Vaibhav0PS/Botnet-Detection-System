# Script to run a new PCAP file and update the dashboard
# Usage: .\run_new_pcap.ps1 Sample_Testing/zeus1-117.10.28.pcap

param(
    [Parameter(Mandatory=$true)]
    [string]$PcapFile
)

Write-Host "=== Running New PCAP Analysis ===" -ForegroundColor Cyan
Write-Host "PCAP File: $PcapFile" -ForegroundColor Yellow

# Step 1: Clear database
Write-Host "`n[1/4] Clearing database..." -ForegroundColor Green
if (Test-Path "backend/botnet_stream.db") {
    Remove-Item "backend/botnet_stream.db" -Force
    Write-Host "Database cleared!" -ForegroundColor Green
}

# Step 2: Run producer
Write-Host "`n[2/4] Replaying PCAP file..." -ForegroundColor Green
python -m producer.pcap_replay_producer $PcapFile --replay-delay 0.3
Write-Host "PCAP replay complete!" -ForegroundColor Green

# Step 3: Wait for consumer to process
Write-Host "`n[3/4] Waiting for ML predictions..." -ForegroundColor Green
Start-Sleep -Seconds 3

# Step 4: Sync database
Write-Host "`n[4/4] Syncing database..." -ForegroundColor Green
python sync_database_once.py

Write-Host "`n=== Analysis Complete! ===" -ForegroundColor Cyan
Write-Host "Dashboard updated at: http://localhost:5173/" -ForegroundColor Yellow
Write-Host "`nAPI Summary:" -ForegroundColor Cyan
$summary = (Invoke-WebRequest -Uri http://localhost:8000/api/summary -UseBasicParsing).Content | ConvertFrom-Json
Write-Host "  Total Flows: $($summary.total_flows)" -ForegroundColor White
Write-Host "  Benign Flows: $($summary.benign_flows)" -ForegroundColor Green
Write-Host "  Botnet Flows: $($summary.botnet_flows)" -ForegroundColor Red
Write-Host "  Total Hosts: $($summary.total_hosts)" -ForegroundColor White
Write-Host "  Botnet Hosts: $($summary.botnet_hosts)" -ForegroundColor Red
