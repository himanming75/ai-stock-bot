$ErrorActionPreference="Stop"

$Repo="C:\stock-bot"
$Port=8766
$Python="$Repo\.venv\Scripts\python.exe"

Set-Location $Repo

Write-Host "=== RESTART V3.17 DASHBOARD ==="

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

Start-Sleep -Seconds 5

$S=Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/status"
$W=$S.trade_analytics.strategy_weakness_map

Write-Host "DASHBOARD PID:" $P.Id
Write-Host "WEAKNESS STATUS:" $W.status
Write-Host "OVERALL SEVERITY:" $W.overall_severity
Write-Host "PRIORITY SCORE:" $W.priority_score
Write-Host "ISSUE COUNT:" $W.issue_count
Write-Host "DASHBOARD RUNTIME: PASS"
