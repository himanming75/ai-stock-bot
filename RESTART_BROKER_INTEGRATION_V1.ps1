$ErrorActionPreference="Stop"

$Repo="C:\stock-bot"
$Port=8766
$Python="$Repo\.venv\Scripts\python.exe"

Set-Location $Repo

Write-Host "=== RESTART BROKER INTEGRATION V1 DASHBOARD ==="

$Old=@(
 Get-NetTCPConnection `
  -LocalPort $Port `
  -State Listen `
  -ErrorAction SilentlyContinue
)

foreach($L in $Old){
 Write-Host "Stopping PID:" $L.OwningProcess
 Stop-Process -Id $L.OwningProcess -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 2

$P=Start-Process `
 -FilePath $Python `
 -ArgumentList @(
  "$Repo\dashboard\operations_dashboard_v3_2.py",
  "--root","$Repo",
  "--host","127.0.0.1",
  "--port","$Port"
 ) `
 -WorkingDirectory $Repo `
 -PassThru

Start-Sleep -Seconds 6

$S=Invoke-RestMethod `
 -Uri "http://127.0.0.1:$Port/api/status"

$B=$S.broker_integration_v1

Write-Host "DASHBOARD PID:" $P.Id
Write-Host "BROKER V1:" $B.status
Write-Host "DEVELOPMENT:" $B.development_status
Write-Host "ETRADE READONLY:" $B.etrade_readonly_status
Write-Host "NETWORK:" $B.network_status
Write-Host "LIVE:" $B.live_trading_status
Write-Host "DUPLICATES:" $B.contracts.duplicate_broker_contract_created "/" $B.contracts.duplicate_alpaca_market_data_stack_created
Write-Host "DASHBOARD RUNTIME: PASS"
