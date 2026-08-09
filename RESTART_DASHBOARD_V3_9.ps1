$ErrorActionPreference="Stop"

$Repo="C:\stock-bot"
$Port=8766
$Python="$Repo\.venv\Scripts\python.exe"

Set-Location $Repo

Write-Host "=== RESTART V3.9 DASHBOARD ==="

$Listeners=@(
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
)
foreach($L in $Listeners){
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

Write-Host "DASHBOARD PID:" $P.Id
Write-Host "CANONICAL STATUS:" $S.trade_analytics.canonical_lifecycle_discovery.status
Write-Host "HISTORICAL CLOSED TRADES:" $S.performance.historical_closed_trades
Write-Host "REALIZED PNL:" $S.performance.historical_realized_pnl
Write-Host "WIN RATE:" $S.performance.win_rate
Write-Host "PROFIT FACTOR:" $S.performance.profit_factor
Write-Host "DAILY PNL POINTS:" $S.visualization.summary.daily_realized_point_count

if($S.trade_analytics_status -ne "PASS"){throw "V3.9 DASHBOARD ANALYTICS FAILED"}

Write-Host "DASHBOARD RUNTIME: PASS"
