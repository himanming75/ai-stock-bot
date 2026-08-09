$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"; $Port=8766; $Python="$Repo\.venv\Scripts\python.exe"
Set-Location $Repo

Write-Host "=== RESTART V3.10 DASHBOARD ==="

$Old=@(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
foreach($L in $Old){
 Write-Host "Stopping PID:" $L.OwningProcess
 Stop-Process -Id $L.OwningProcess -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 2

$P=Start-Process -FilePath $Python -ArgumentList @(
 "$Repo\dashboard\operations_dashboard_v3_2.py",
 "--root","$Repo","--host","127.0.0.1","--port","$Port"
) -WorkingDirectory $Repo -PassThru

Start-Sleep -Seconds 5
$S=Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/status"

Write-Host "DASHBOARD PID:" $P.Id
Write-Host "CANONICAL STATUS:" $S.trade_analytics.canonical_lifecycle_discovery.status
Write-Host "TRADE DETAIL ROWS:" @($S.trade_analytics.trade_details).Count
Write-Host "NUMERIC TRADES:" $S.trade_analytics.historical.numeric_trade_count
Write-Host "DASHBOARD RUNTIME: PASS"
