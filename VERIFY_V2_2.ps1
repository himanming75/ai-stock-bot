$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}
& $Python -m unittest .\tests\test_expected_return_cancellation_v2_2.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
$p=".\runtime\real_market_multitimeframe_shadow\latest_expected_return_cancellation_v2_2.json"
if(-not(Test-Path $p)){throw "V2.2 RESULT MISSING"}
$r=Get-Content $p -Raw|ConvertFrom-Json
if($r.status -ne "PASS"){throw "V2.2 NOT PASS"}
if($r.interpretation_contract.timeframe_weights_changed -ne $false){throw "TIMEFRAME WEIGHT CHANGED"}
if($r.interpretation_contract.expected_return_formula_changed -ne $false){throw "EXPECTED RETURN FORMULA CHANGED"}
if($r.contracts.broker_write_performed -ne $false){throw "BROKER WRITE"}
if($r.contracts.order_submission_performed -ne $false){throw "ORDER SUBMISSION"}
Write-Host ""
Write-Host "BUY CANCELLATION SUMMARY:"
$r.buy_summary|Select-Object count,abs_expected_return,reward_risk,cancellation_ratio,opposite_direction_contribution_abs|ConvertTo-Json -Depth 8
Write-Host ""
Write-Host "SELL CANCELLATION SUMMARY:"
$r.sell_summary|Select-Object count,abs_expected_return,reward_risk,cancellation_ratio,opposite_direction_contribution_abs|ConvertTo-Json -Depth 8
Write-Host ""
Write-Host "BUY TIMEFRAME CONTRIBUTION:"
$r.buy_summary.timeframe_decomposition|ConvertTo-Json -Depth 10
Write-Host ""
Write-Host "SELL TIMEFRAME CONTRIBUTION:"
$r.sell_summary.timeframe_decomposition|ConvertTo-Json -Depth 10
Write-Host ""
Write-Host "COMPARISON:"
$r.comparison|ConvertTo-Json -Depth 8
Write-Host ""
Write-Host "VERIFY: PASS"
