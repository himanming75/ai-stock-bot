$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}
& $Python -m unittest .\tests\test_signal_coverage_v1_8.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
$p=".\runtime\real_market_multitimeframe_shadow\latest_signal_coverage_decomposition_v1_8.json"
if(-not(Test-Path $p)){throw "V1.8 RESULT MISSING"}
$r=Get-Content $p -Raw|ConvertFrom-Json
if($r.status -ne "PASS"){throw "V1.8 NOT PASS"}
if($r.contracts.paper_runtime_modified -ne $false){throw "PAPER RUNTIME MODIFIED"}
if($r.contracts.production_parameter_modified -ne $false){throw "PRODUCTION PARAMETER MODIFIED"}
if($r.contracts.broker_write_performed -ne $false){throw "BROKER WRITE"}
if($r.contracts.order_submission_performed -ne $false){throw "ORDER SUBMISSION"}
if($r.contracts.duplicate_engine_created -ne $false){throw "DUPLICATE ENGINE"}
Write-Host ""
Write-Host "SELL DECOMPOSITION:"
$r.sell_decomposition|ConvertTo-Json -Depth 8
Write-Host ""
Write-Host "CONFIDENCE DECOMPOSITION:"
$r.confidence_decomposition|ConvertTo-Json -Depth 8
Write-Host ""
Write-Host "FEATURE COVERAGE:"
$r.feature_coverage_decomposition|Select-Object affected_checkpoint_count,affected_checkpoints_by_date,rejected_symbol_counts,missing_symbol_timeframe_counts|ConvertTo-Json -Depth 8
Write-Host ""
Write-Host "BUY-LIKE BUT BLOCKED COUNT:" $r.buy_like_but_blocked.count
Write-Host ""
Write-Host "VERIFY: PASS"
