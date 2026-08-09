$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

$Python="C:\stock-bot\.venv\Scripts\python.exe"
$Port=8878

Write-Host "=== V3.8.1 DIRECT SERVER VERIFY ==="

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

$P=Start-Process `
    -FilePath $Python `
    -ArgumentList @(
        "C:\stock-bot\dashboard\operations_dashboard_v3_2.py",
        "--root","C:\stock-bot",
        "--host","127.0.0.1",
        "--port","$Port"
    ) `
    -WorkingDirectory "C:\stock-bot" `
    -PassThru

try{
    Start-Sleep -Seconds 5

    $S=Invoke-RestMethod `
        -Uri "http://127.0.0.1:$Port/api/status" `
        -TimeoutSec 20

    $A=$S.trade_analytics
    $L=$A.canonical_lifecycle_discovery

    Write-Host "VISUALIZATION STATUS:" $S.visualization_status
    Write-Host "TRADE ANALYTICS STATUS:" $S.trade_analytics_status
    Write-Host "CANONICAL STATUS:" $L.status
    Write-Host "CANONICAL FILE EXISTS:" $L.existence.closed_round_trips
    Write-Host "CANONICAL ROWS:" $L.counts.canonical_closed_round_trip_rows
    Write-Host "CANONICAL NUMERIC PNL:" $L.counts.canonical_numeric_pnl_count
    Write-Host "ANALYTICS TRADES:" $A.historical.observed_closed_trade_count
    Write-Host "ANALYTICS NUMERIC TRADES:" $A.historical.numeric_trade_count
    Write-Host "NET REALIZED PNL:" $A.historical.net_realized_pnl
    Write-Host "EXIT SUBMISSION ROWS:" $L.counts.exit_submission_rows
    Write-Host "OPEN REGISTRY POSITIONS:" $L.counts.open_registry_position_count
    Write-Host "SOURCE OF TRUTH:" $L.source_of_truth

    if($S.visualization_status -ne "PASS"){
        throw "VISUALIZATION REGRESSION"
    }

    if($S.trade_analytics_status -like "ISOLATED_*"){
        throw "TRADE ANALYTICS ERROR"
    }

    if($L.counts.canonical_numeric_pnl_count -gt 0){
        if($A.historical.numeric_trade_count -ne $L.counts.canonical_numeric_pnl_count){
            throw "CANONICAL COUNT MISMATCH"
        }
    }

    Write-Host "DIRECT SERVER VERIFY: PASS"
}
finally{
    Stop-Process `
        -Id $P.Id `
        -Force `
        -ErrorAction SilentlyContinue
}

Write-Host "VERIFY: PASS"
