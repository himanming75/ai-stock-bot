$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$Port=8882
Write-Host "=== V3.12 DIRECT SERVER VERIFY ==="
$Old=@(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
foreach($L in $Old){Stop-Process -Id $L.OwningProcess -Force -ErrorAction SilentlyContinue}
$P=Start-Process -FilePath $Python -ArgumentList @("C:\stock-bot\dashboard\operations_dashboard_v3_2.py","--root","C:\stock-bot","--host","127.0.0.1","--port","$Port") -WorkingDirectory "C:\stock-bot" -PassThru
try{
 Start-Sleep -Seconds 5
 $S=Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/status" -TimeoutSec 20
 $R=$S.trade_analytics.strategy_readiness
 Write-Host "VISUALIZATION STATUS:" $S.visualization_status
 Write-Host "TRADE ANALYTICS STATUS:" $S.trade_analytics_status
 Write-Host "CANONICAL STATUS:" $S.trade_analytics.canonical_lifecycle_discovery.status
 Write-Host "READINESS STATUS:" $R.status
 Write-Host "OVERALL SCORE:" $R.overall_score
 Write-Host "RAW OVERALL SCORE:" $R.raw_overall_score
 Write-Host "SAMPLE SCORE:" $R.scores.sample_confidence
 Write-Host "PROFITABILITY SCORE:" $R.scores.profitability_quality
 Write-Host "RISK SCORE:" $R.scores.risk_quality
 Write-Host "CONSISTENCY SCORE:" $R.scores.consistency
 Write-Host "DIVERSIFICATION SCORE:" $R.scores.diversification
 Write-Host "CANONICAL TRADE COUNT:" $R.canonical_numeric_trade_count
 Write-Host "BLOCKER COUNT:" @($R.blockers).Count
 if($S.visualization_status -ne "PASS"){throw "VISUALIZATION REGRESSION"}
 if($S.trade_analytics_status -ne "PASS"){throw "TRADE ANALYTICS NOT PASS"}
 if($R.canonical_numeric_trade_count -ne $S.trade_analytics.historical.numeric_trade_count){throw "READINESS COUNT MISMATCH"}
 if($R.canonical_numeric_trade_count -lt $R.thresholds.minimum_evaluation_trades -and $R.status -ne "NOT_READY"){throw "SAMPLE HARD GATE FAILED"}
 if($R.contracts.automatic_promotion){throw "AUTOMATIC PROMOTION CONTRACT FAILED"}
 if($R.contracts.live_approval){throw "LIVE APPROVAL CONTRACT FAILED"}
 if($R.contracts.broker_write_performed){throw "BROKER WRITE CONTRACT FAILED"}
 Write-Host "=== UTF8 UI VERIFY ==="
 & $Python .\dashboard\verify_strategy_readiness_utf8_v3_12.py --url "http://127.0.0.1:$Port/"
 if($LASTEXITCODE -ne 0){throw "V3.12 UTF8 UI VERIFY FAILED"}
 Write-Host "DIRECT SERVER VERIFY: PASS"
}
finally{Stop-Process -Id $P.Id -Force -ErrorAction SilentlyContinue}
Write-Host "VERIFY: PASS"
