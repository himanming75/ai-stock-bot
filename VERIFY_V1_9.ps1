$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}
& $Python -m unittest .\tests\test_pre_threshold_buy_recovery_v1_9.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
$p=".\runtime\real_market_multitimeframe_shadow\latest_pre_threshold_buy_recovery_v1_9.json"
if(-not(Test-Path $p)){throw "V1.9 RESULT MISSING"}
$r=Get-Content $p -Raw|ConvertFrom-Json
if($r.status -ne "PASS"){throw "V1.9 NOT PASS"}
if($r.interpretation_contract.threshold_change_applied_to_production -ne $false){throw "PRODUCTION THRESHOLD CHANGED"}
if($r.interpretation_contract.raw_confidence_applied_to_production -ne $false){throw "RAW CONFIDENCE APPLIED"}
if($r.warmup_normalization.synthetic_1d_data_created -ne $false){throw "SYNTHETIC WARMUP DATA"}
if($r.contracts.broker_write_performed -ne $false){throw "BROKER WRITE"}
if($r.contracts.order_submission_performed -ne $false){throw "ORDER SUBMISSION"}
Write-Host ""
Write-Host "WARMUP NORMALIZATION:"
$r.warmup_normalization|ConvertTo-Json -Depth 8
Write-Host ""
Write-Host "CALIBRATED THRESHOLD SENSITIVITY:"
$r.confidence_counterfactual.calibrated_confidence|ConvertTo-Json -Depth 8
Write-Host ""
Write-Host "RAW CONFIDENCE SENSITIVITY:"
$r.confidence_counterfactual.raw_confidence|ConvertTo-Json -Depth 8
Write-Host ""
Write-Host "RAW VS CALIBRATED @ 0.75:"
$r.confidence_counterfactual.at_0_75|Select-Object canonical_calibrated_buy_selected_count,raw_confidence_buy_selected_count,selection_changed_checkpoint_count|ConvertTo-Json
Write-Host ""
Write-Host "MSFT SELL TIMEFRAME COUNTS:"
$r.msft_sell_bias_decomposition.timeframe_signal_counts_on_msft_selected_sell|ConvertTo-Json -Depth 8
Write-Host ""
Write-Host "VERIFY: PASS"
