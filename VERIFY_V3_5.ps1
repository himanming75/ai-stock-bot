$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$TestPort=8875
Write-Host "=== V3.5 DIRECT-SCRIPT SERVER VERIFY ==="
$Existing=@(Get-NetTCPConnection -LocalPort $TestPort -State Listen -ErrorAction SilentlyContinue)
foreach($L in $Existing){Stop-Process -Id $L.OwningProcess -Force -ErrorAction SilentlyContinue}
$Proc=Start-Process -FilePath $Python -ArgumentList @("C:\stock-bot\dashboard\operations_dashboard_v3_2.py","--root","C:\stock-bot","--host","127.0.0.1","--port","$TestPort") -WorkingDirectory "C:\stock-bot" -PassThru
try{
 Start-Sleep -Seconds 4
 $Status=Invoke-RestMethod -Uri "http://127.0.0.1:$TestPort/api/status" -TimeoutSec 15
 Write-Host "VISUALIZATION STATUS:" $Status.visualization_status
 Write-Host "TRADE ANALYTICS STATUS:" $Status.trade_analytics_status
 Write-Host "OBSERVED CLOSED TRADES:" $Status.trade_analytics.historical.observed_closed_trade_count
 Write-Host "NUMERIC TRADES:" $Status.trade_analytics.historical.numeric_trade_count
 Write-Host "NET REALIZED PNL:" $Status.trade_analytics.historical.net_realized_pnl
 Write-Host "WIN RATE:" $Status.trade_analytics.historical.win_rate
 Write-Host "PROFIT FACTOR:" $Status.trade_analytics.historical.profit_factor
 Write-Host "MAX REALIZED DRAWDOWN:" $Status.trade_analytics.historical.max_realized_drawdown
 Write-Host "VALIDATION STATUS:" $Status.trade_analytics.validation.data_status
 Write-Host "SYMBOL GROUPS:" $Status.trade_analytics.by_symbol.Count
 Write-Host "EXIT REASON GROUPS:" $Status.trade_analytics.by_exit_reason.Count
 if($Status.visualization_status -ne "PASS"){throw "V3.4 VISUALIZATION REGRESSION"}
 if($Status.trade_analytics_status -like "ISOLATED_*"){throw "V3.5 TRADE ANALYTICS ERROR"}
 if(-not $Status.trade_analytics.contracts.read_only){throw "V3.5 READ-ONLY CONTRACT FAILED"}
 if($Status.trade_analytics.contracts.order_submission_performed){throw "V3.5 ORDER SUBMISSION CONTRACT FAILED"}
 Write-Host "DIRECT SERVER VERIFY: PASS"
} finally {Stop-Process -Id $Proc.Id -Force -ErrorAction SilentlyContinue}
Write-Host "VERIFY: PASS"
