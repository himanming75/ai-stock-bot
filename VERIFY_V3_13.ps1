$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$Port=8883
Write-Host "=== V3.13 DIRECT SERVER VERIFY ==="
$Old=@(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
foreach($L in $Old){Stop-Process -Id $L.OwningProcess -Force -ErrorAction SilentlyContinue}
$P=Start-Process -FilePath $Python -ArgumentList @("C:\stock-bot\dashboard\operations_dashboard_v3_2.py","--root","C:\stock-bot","--host","127.0.0.1","--port","$Port") -WorkingDirectory "C:\stock-bot" -PassThru
try{
 Start-Sleep -Seconds 5
 $S=Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/status" -TimeoutSec 20
 $H=$S.trade_analytics.readiness_history
 $R=$S.trade_analytics.strategy_readiness
 Write-Host "VISUALIZATION STATUS:" $S.visualization_status
 Write-Host "TRADE ANALYTICS STATUS:" $S.trade_analytics_status
 Write-Host "READINESS STATUS:" $R.status
 Write-Host "HISTORY STATUS:" $H.status
 Write-Host "HISTORY RECORD COUNT:" $H.history_record_count
 Write-Host "HISTORY WRITE:" $H.write_result.written
 Write-Host "HISTORY WRITE REASON:" $H.write_result.reason
 Write-Host "LATEST SCORE:" $H.latest.overall_score
 Write-Host "LATEST TRADE COUNT:" $H.latest.canonical_numeric_trade_count
 Write-Host "NEXT MILESTONE:" $H.milestones.next_milestone
 Write-Host "STATUS CHANGE COUNT:" @($H.status_changes).Count
 Write-Host "TREND POINT COUNT:" @($H.trend).Count
 Write-Host "HISTORY FILE:" $H.history_file
 if($S.visualization_status -ne "PASS"){throw "VISUALIZATION REGRESSION"}
 if($S.trade_analytics_status -ne "PASS"){throw "TRADE ANALYTICS NOT PASS"}
 if($H.status -ne "PASS"){throw "HISTORY STATUS NOT PASS"}
 if($H.history_record_count -lt 1){throw "NO HISTORY RECORD"}
 if($H.latest.canonical_numeric_trade_count -ne $R.canonical_numeric_trade_count){throw "LATEST HISTORY TRADE COUNT MISMATCH"}
 if($H.contracts.broker_write_performed){throw "BROKER WRITE CONTRACT FAILED"}
 if($H.contracts.paper_runtime_modified){throw "PAPER RUNTIME CONTRACT FAILED"}
 if(-not $H.contracts.analytics_history_write_only){throw "HISTORY WRITE CONTRACT FAILED"}
 Write-Host "=== UTF8 UI VERIFY ==="
 & $Python .\dashboard\verify_readiness_history_utf8_v3_13.py --url "http://127.0.0.1:$Port/"
 if($LASTEXITCODE -ne 0){throw "V3.13 UTF8 UI VERIFY FAILED"}
 Write-Host "DIRECT SERVER VERIFY: PASS"
}
finally{Stop-Process -Id $P.Id -Force -ErrorAction SilentlyContinue}
Write-Host "VERIFY: PASS"
