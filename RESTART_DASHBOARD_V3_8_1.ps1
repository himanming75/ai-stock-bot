$ErrorActionPreference="Stop"

$Repo="C:\stock-bot"
$Port=8766
$Python="$Repo\.venv\Scripts\python.exe"

Set-Location $Repo

$Old=@(
    Get-NetTCPConnection `
        -LocalPort $Port `
        -State Listen `
        -ErrorAction SilentlyContinue
)

foreach($L in $Old){
    Stop-Process `
        -Id $L.OwningProcess `
        -Force `
        -ErrorAction SilentlyContinue
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

$S=Invoke-RestMethod `
    -Uri "http://127.0.0.1:$Port/api/status"

$L=$S.trade_analytics.canonical_lifecycle_discovery

Write-Host "DASHBOARD PID:" $P.Id
Write-Host "CANONICAL STATUS:" $L.status
Write-Host "NUMERIC TRADES:" $S.trade_analytics.historical.numeric_trade_count
Write-Host "NET REALIZED PNL:" $S.trade_analytics.historical.net_realized_pnl
Write-Host "DASHBOARD RUNTIME: PASS"
