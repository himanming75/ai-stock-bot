$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

$Python="C:\stock-bot\.venv\Scripts\python.exe"
$Port=8887

Write-Host "=== V3.17 DIRECT SERVER VERIFY ==="

$Old=@(
 Get-NetTCPConnection `
  -LocalPort $Port `
  -State Listen `
  -ErrorAction SilentlyContinue
)
foreach($L in $Old){
 Stop-Process -Id $L.OwningProcess -Force -ErrorAction SilentlyContinue
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

 $S=Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/status" -TimeoutSec 20
 $W=$S.trade_analytics.strategy_weakness_map

 Write-Host "VISUALIZATION STATUS:" $S.visualization_status
 Write-Host "TRADE ANALYTICS STATUS:" $S.trade_analytics_status
 Write-Host "WEAKNESS STATUS:" $W.status
 Write-Host "OVERALL SEVERITY:" $W.overall_severity
 Write-Host "PRIORITY SCORE:" $W.priority_score
 Write-Host "ISSUE COUNT:" $W.issue_count
 Write-Host "EVIDENCE GAP COUNT:" $W.type_counts.EVIDENCE_GAP
 Write-Host "PERFORMANCE RISK COUNT:" $W.type_counts.PERFORMANCE_RISK
 Write-Host "CRITICAL COUNT:" $W.severity_counts.CRITICAL
 Write-Host "HIGH COUNT:" $W.severity_counts.HIGH

 foreach($Issue in @($W.top_priorities)){
   Write-Host "--- PRIORITY ---"
   Write-Host "CODE:" $Issue.code
   Write-Host "SEVERITY:" $Issue.severity
   Write-Host "TYPE:" $Issue.weakness_type
   Write-Host "CATEGORY:" $Issue.category
   Write-Host "TITLE:" $Issue.title
 }

 if($S.visualization_status -ne "PASS"){throw "VISUALIZATION REGRESSION"}
 if($S.trade_analytics_status -ne "PASS"){throw "TRADE ANALYTICS NOT PASS"}
 if($W.status -ne "PASS"){throw "WEAKNESS MAP STATUS NOT PASS"}
 if(-not $W.contracts.diagnostic_only){throw "DIAGNOSTIC CONTRACT FAILED"}
 if(-not $W.contracts.evidence_gap_not_equal_strategy_failure){throw "EVIDENCE GAP CONTRACT FAILED"}
 if($W.contracts.automatic_parameter_change){throw "AUTO PARAMETER CHANGE CONTRACT FAILED"}
 if($W.contracts.automatic_strategy_change){throw "AUTO STRATEGY CHANGE CONTRACT FAILED"}
 if($W.contracts.automatic_promotion){throw "AUTO PROMOTION CONTRACT FAILED"}
 if($W.contracts.broker_write_performed){throw "BROKER WRITE CONTRACT FAILED"}
 if($W.contracts.paper_runtime_modified){throw "PAPER RUNTIME CONTRACT FAILED"}
 if($W.contracts.live_approval){throw "LIVE APPROVAL CONTRACT FAILED"}

 $Count=[int]$S.trade_analytics.historical.numeric_trade_count
 if($Count -lt 10){
   $SampleIssue=@($W.issues | Where-Object {$_.code -eq "SAMPLE_SIZE_INSUFFICIENT"})
   if($SampleIssue.Count -ne 1){throw "SAMPLE WEAKNESS GUARD FAILED"}
   if($SampleIssue[0].weakness_type -ne "EVIDENCE_GAP"){throw "SAMPLE TYPE GUARD FAILED"}
 }

 Write-Host "=== UTF8 UI VERIFY ==="

 & $Python .\dashboard\verify_strategy_weakness_utf8_v3_17.py --url "http://127.0.0.1:$Port/"
 if($LASTEXITCODE -ne 0){throw "V3.17 UTF8 UI VERIFY FAILED"}

 Write-Host "DIRECT SERVER VERIFY: PASS"
}
finally{
 Stop-Process -Id $P.Id -Force -ErrorAction SilentlyContinue
}

Write-Host "VERIFY: PASS"
