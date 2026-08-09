$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}

& $Python -m unittest .\tests\test_regime_aware_buy_walkforward_oos_v2_6.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

$p=".\runtime\real_market_multitimeframe_shadow\latest_regime_aware_buy_walkforward_oos_v2_6.json"
if(-not(Test-Path $p)){throw "V2.6 RESULT MISSING"}

$r=Get-Content $p -Raw|ConvertFrom-Json

if($r.status -ne "PASS"){throw "V2.6 NOT PASS"}
if($r.windowing.candidate_selection_reopened -ne $false){throw "CANDIDATE SELECTION REOPENED"}
if($r.interpretation_contract.candidate_reoptimized -ne $false){throw "CANDIDATE REOPTIMIZED"}
if($r.interpretation_contract.production_change_applied -ne $false){throw "PRODUCTION CHANGE"}
if($r.contracts.broker_write_performed -ne $false){throw "BROKER WRITE"}
if($r.contracts.order_submission_performed -ne $false){throw "ORDER SUBMISSION"}

Write-Host ""
Write-Host "DIAGNOSTIC ACCEPTANCE:"
$r.diagnostic_acceptance|ConvertTo-Json -Depth 10

Write-Host ""
Write-Host "MSFT ONLY - 5BPS:"
$r.fixed_candidates.MSFT_ONLY_30M.stress.'5'|ConvertTo-Json -Depth 10

Write-Host ""
Write-Host "MSFT ONLY - 10BPS:"
$r.fixed_candidates.MSFT_ONLY_30M.stress.'10'|ConvertTo-Json -Depth 10

Write-Host ""
Write-Host "MSFT+NVDA - 5BPS:"
$r.fixed_candidates.MSFT_NVDA_30M.stress.'5'|ConvertTo-Json -Depth 10

Write-Host ""
Write-Host "MSFT+NVDA - 10BPS:"
$r.fixed_candidates.MSFT_NVDA_30M.stress.'10'|ConvertTo-Json -Depth 10

Write-Host ""
Write-Host "VERIFY: PASS"
