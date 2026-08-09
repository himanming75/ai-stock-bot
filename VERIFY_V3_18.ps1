$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe";$Port=8888
$Old=@(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue);foreach($L in $Old){Stop-Process -Id $L.OwningProcess -Force -ErrorAction SilentlyContinue}
$P=Start-Process -FilePath $Python -ArgumentList @("C:\stock-bot\dashboard\operations_dashboard_v3_2.py","--root","C:\stock-bot","--host","127.0.0.1","--port","$Port") -WorkingDirectory "C:\stock-bot" -PassThru
try{
 Start-Sleep -Seconds 5;$S=Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/status" -TimeoutSec 20;$I=$S.trade_analytics.strategy_improvement_candidates
 Write-Host "IMPROVEMENT STATUS:" $I.status;Write-Host "MODE:" $I.mode;Write-Host "CANONICAL NUMERIC TRADES:" $I.canonical_numeric_trade_count;Write-Host "CANDIDATE COUNT:" $I.candidate_count;Write-Host "EVIDENCE CANDIDATES:" $I.evidence_collection_candidate_count;Write-Host "STRATEGY CANDIDATES:" $I.strategy_change_candidate_count
 if($S.visualization_status -ne "PASS"){throw "VISUALIZATION REGRESSION"};if($S.trade_analytics_status -ne "PASS"){throw "TRADE ANALYTICS NOT PASS"};if($I.status -ne "PASS"){throw "IMPROVEMENT STATUS NOT PASS"}
 if($I.contracts.automatic_strategy_change -or $I.contracts.automatic_parameter_change -or $I.contracts.paper_parameter_change -or $I.contracts.live_change -or $I.contracts.broker_write_performed -or $I.contracts.order_submission_performed){throw "V3.18 SAFETY CONTRACT FAILED"}
 if([int]$I.canonical_numeric_trade_count -lt 10 -and $I.mode -ne "EVIDENCE_COLLECTION_ONLY"){throw "SMALL SAMPLE MODE FAILED"}
 & $Python .\dashboard\verify_strategy_improvement_utf8_v3_18.py --url "http://127.0.0.1:$Port/";if($LASTEXITCODE -ne 0){throw "UTF8 UI VERIFY FAILED"}
 Write-Host "DIRECT SERVER VERIFY: PASS"
}finally{Stop-Process -Id $P.Id -Force -ErrorAction SilentlyContinue}
Write-Host "VERIFY: PASS"
