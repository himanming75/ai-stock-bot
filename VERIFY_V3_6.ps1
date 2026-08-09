$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

$Python="C:\stock-bot\.venv\Scripts\python.exe"
$TestPort=8876

Write-Host "=== V3.6 DIRECT SERVER VERIFY ==="

$Existing=@(
    Get-NetTCPConnection -LocalPort $TestPort -State Listen -ErrorAction SilentlyContinue
)
foreach($L in $Existing){
    Stop-Process -Id $L.OwningProcess -Force -ErrorAction SilentlyContinue
}

$Proc=Start-Process `
    -FilePath $Python `
    -ArgumentList @(
        "C:\stock-bot\dashboard\operations_dashboard_v3_2.py",
        "--root", "C:\stock-bot",
        "--host", "127.0.0.1",
        "--port", "$TestPort"
    ) `
    -WorkingDirectory "C:\stock-bot" `
    -PassThru

try{
    Start-Sleep -Seconds 4
    $Status=Invoke-RestMethod `
        -Uri "http://127.0.0.1:$TestPort/api/status" `
        -TimeoutSec 15

    $A=$Status.trade_analytics
    $R=$A.recovery_audit

    Write-Host "VISUALIZATION STATUS:" $Status.visualization_status
    Write-Host "TRADE ANALYTICS STATUS:" $Status.trade_analytics_status
    Write-Host "OBSERVED CLOSED TRADES:" $A.historical.observed_closed_trade_count
    Write-Host "NUMERIC TRADES:" $A.historical.numeric_trade_count
    Write-Host "NET REALIZED PNL:" $A.historical.net_realized_pnl
    Write-Host "WIN RATE:" $A.historical.win_rate
    Write-Host "PROFIT FACTOR:" $A.historical.profit_factor
    Write-Host "RECOVERED NUMERIC PNL:" $R.numeric_pnl_recovered_count
    Write-Host "MISSING NUMERIC PNL:" $R.numeric_pnl_missing_count
    Write-Host "RECOVERY RATE:" $R.recovery_rate
    Write-Host "PNL PATH COUNTS:" ($R.pnl_path_counts | ConvertTo-Json -Compress)
    Write-Host "RECOVERY STATUS:" $R.recovery_status

    if($Status.visualization_status -ne "PASS"){
        throw "V3.4 VISUALIZATION REGRESSION"
    }
    if($Status.trade_analytics_status -like "ISOLATED_*"){
        throw "V3.6 ANALYTICS INTEGRATION ERROR"
    }
    if($R.observed_closed_trade_count -lt 1){
        throw "NO CLOSED TRADE RECORDS FOUND"
    }
    if($A.historical.numeric_trade_count -ne $R.numeric_pnl_recovered_count){
        throw "NORMALIZED PNL COUNT MISMATCH"
    }

    Write-Host "DIRECT SERVER VERIFY: PASS"
}
finally{
    Stop-Process -Id $Proc.Id -Force -ErrorAction SilentlyContinue
}

Write-Host "VERIFY: PASS"
