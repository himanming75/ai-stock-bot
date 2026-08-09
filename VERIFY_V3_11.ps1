$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$Port=8881
Write-Host "=== V3.11 DIRECT SERVER VERIFY ==="
$Old=@(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
foreach($L in $Old){Stop-Process -Id $L.OwningProcess -Force -ErrorAction SilentlyContinue}
$P=Start-Process -FilePath $Python -ArgumentList @("C:\stock-bot\dashboard\operations_dashboard_v3_2.py","--root","C:\stock-bot","--host","127.0.0.1","--port","$Port") -WorkingDirectory "C:\stock-bot" -PassThru
try{
 Start-Sleep -Seconds 5
 $S=Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/status" -TimeoutSec 20
 $D=$S.trade_analytics.performance_diagnostics
 Write-Host "VISUALIZATION STATUS:" $S.visualization_status
 Write-Host "TRADE ANALYTICS STATUS:" $S.trade_analytics_status
 Write-Host "CANONICAL STATUS:" $S.trade_analytics.canonical_lifecycle_discovery.status
 Write-Host "DIAGNOSTICS STATUS:" $D.status
 Write-Host "DIAGNOSTIC TRADE COUNT:" $D.canonical_numeric_trade_count
 Write-Host "MINIMUM SAMPLE:" $D.minimum_sample_required
 Write-Host "BEST TRADE PNL:" $D.best_trade.pnl
 Write-Host "WORST TRADE PNL:" $D.worst_trade.pnl
 Write-Host "AVERAGE HOLDING MINUTES:" $D.average_holding_minutes
 Write-Host "MAX WIN STREAK:" $D.streaks.max_consecutive_wins
 Write-Host "MAX LOSS STREAK:" $D.streaks.max_consecutive_losses
 Write-Host "SYMBOL GROUPS:" @($D.by_symbol).Count
 Write-Host "EXIT REASON GROUPS:" @($D.by_exit_reason).Count
 Write-Host "DATE GROUPS:" @($D.by_date).Count
 Write-Host "DIAGNOSTIC NOTES:" @($D.notes).Count
 if($S.visualization_status -ne "PASS"){throw "VISUALIZATION REGRESSION"}
 if($S.trade_analytics_status -ne "PASS"){throw "TRADE ANALYTICS NOT PASS"}
 if($D.canonical_numeric_trade_count -ne $S.trade_analytics.historical.numeric_trade_count){throw "DIAGNOSTIC COUNT MISMATCH"}
 if($D.canonical_numeric_trade_count -lt $D.minimum_sample_required -and $D.status -ne "INSUFFICIENT_SAMPLE"){throw "SAMPLE GUARD FAILED"}
 if($D.contracts.broker_write_performed){throw "BROKER WRITE CONTRACT FAILED"}
 Write-Host "=== UTF8 UI VERIFY ==="
 & $Python .\dashboard\verify_performance_diagnostics_utf8_v3_11.py --url "http://127.0.0.1:$Port/"
 if($LASTEXITCODE -ne 0){throw "V3.11 UTF8 UI VERIFY FAILED"}
 Write-Host "DIRECT SERVER VERIFY: PASS"
}
finally{Stop-Process -Id $P.Id -Force -ErrorAction SilentlyContinue}
Write-Host "VERIFY: PASS"
