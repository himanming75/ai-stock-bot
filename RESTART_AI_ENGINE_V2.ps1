$ErrorActionPreference="Stop"

$Repo="C:\stock-bot"
$Port=8766
$Python="$Repo\.venv\Scripts\python.exe"

Set-Location $Repo

Write-Host "=== RESTART AI ENGINE V2 DASHBOARD ==="

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

$A=$S.trade_analytics.ai_engine_v2

Write-Host "DASHBOARD PID:" $P.Id
Write-Host "AI ENGINE V2 STATUS:" $A.status
Write-Host "DEVELOPMENT:" $A.development_status
Write-Host "REAL EVIDENCE:" $A.real_evidence_status
Write-Host "LIVE:" $A.live_trading_status
Write-Host "AUTO PROMOTION:" $A.automatic_promotion_status
Write-Host "DASHBOARD RUNTIME: PASS"
