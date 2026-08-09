$ErrorActionPreference="Stop"

$Repo="C:\stock-bot"
$Port=8766
$Python="$Repo\.venv\Scripts\python.exe"
Set-Location $Repo

Write-Host "=== RESTART V3.6 DASHBOARD ==="

$Listeners=@(
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
)
foreach($L in $Listeners){
    Write-Host "Stopping PID:" $L.OwningProcess
    Stop-Process -Id $L.OwningProcess -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 2

$Proc=Start-Process `
    -FilePath $Python `
    -ArgumentList @(
        "$Repo\dashboard\operations_dashboard_v3_2.py",
        "--root", "$Repo",
        "--host", "127.0.0.1",
        "--port", "$Port"
    ) `
    -WorkingDirectory $Repo `
    -PassThru

Start-Sleep -Seconds 4

$Status=Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/status"

Write-Host "DASHBOARD PID:" $Proc.Id
Write-Host "TRADE ANALYTICS STATUS:" $Status.trade_analytics_status
Write-Host "NUMERIC TRADES:" $Status.trade_analytics.historical.numeric_trade_count
Write-Host "NET REALIZED PNL:" $Status.trade_analytics.historical.net_realized_pnl
Write-Host "RECOVERY STATUS:" $Status.trade_analytics.recovery_audit.recovery_status

if($Status.trade_analytics_status -like "ISOLATED_*"){
    throw "V3.6 DASHBOARD ANALYTICS FAILED"
}

Write-Host "DASHBOARD RUNTIME: PASS"
