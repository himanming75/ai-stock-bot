$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}

& $Python -m unittest .\tests\test_regime_aware_buy_v2_5.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

$p=".\runtime\real_market_multitimeframe_shadow\latest_regime_aware_buy_counterfactual_v2_5.json"
if(-not(Test-Path $p)){throw "V2.5 RESULT MISSING"}

$r=Get-Content $p -Raw|ConvertFrom-Json

if($r.status -ne "PASS"){throw "V2.5 NOT PASS"}
if($r.interpretation_contract.production_change_applied -ne $false){throw "PRODUCTION CHANGE"}
if($r.interpretation_contract.regime_rule_applied_to_production -ne $false){throw "REGIME RULE APPLIED"}
if($r.contracts.broker_write_performed -ne $false){throw "BROKER WRITE"}
if($r.contracts.order_submission_performed -ne $false){throw "ORDER SUBMISSION"}

Write-Host ""
Write-Host "TOP DIAGNOSTIC CANDIDATE:"
$r.top_diagnostic_candidate|ConvertTo-Json -Depth 8

Write-Host ""
Write-Host "SURVIVING CANDIDATES:"
$r.surviving_diagnostic_candidates|ConvertTo-Json -Depth 8

Write-Host ""
Write-Host "MSFT+NVDA 45M DEDUP / 5BPS:"
$r.scenario_matrix.MSFT_NVDA.'45'.'5'|ConvertTo-Json -Depth 10

Write-Host ""
Write-Host "ALL 45M DEDUP / 5BPS:"
$r.scenario_matrix.ALL.'45'.'5'|ConvertTo-Json -Depth 10

Write-Host ""
Write-Host "VERIFY: PASS"
