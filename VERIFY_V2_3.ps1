$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}
& $Python -m unittest .\tests\test_1d_regime_conflict_outcome_v2_3.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
$p=".\runtime\real_market_multitimeframe_shadow\latest_1d_regime_conflict_outcome_v2_3.json"
if(-not(Test-Path $p)){throw "V2.3 RESULT MISSING"}
$r=Get-Content $p -Raw|ConvertFrom-Json
if($r.status -ne "PASS"){throw "V2.3 NOT PASS"}
if($r.interpretation_contract.one_day_weight_changed -ne $false){throw "1D WEIGHT CHANGED"}
if($r.interpretation_contract.production_change_applied -ne $false){throw "PRODUCTION CHANGE"}
if($r.contracts.broker_write_performed -ne $false){throw "BROKER WRITE"}
if($r.contracts.order_submission_performed -ne $false){throw "ORDER SUBMISSION"}
Write-Host ""
Write-Host "1D GROUP SUMMARIES:"
$r.group_summaries|ConvertTo-Json -Depth 10
Write-Host ""
Write-Host "OVERALL:"
$r.overall|ConvertTo-Json -Depth 8
Write-Host ""
Write-Host "COUNTERFACTUAL CONTRACT:"
$r.counterfactual_contract|ConvertTo-Json -Depth 8
Write-Host ""
Write-Host "VERIFY: PASS"
