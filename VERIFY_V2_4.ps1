$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}
& $Python -m unittest .\tests\test_1d_opposite_buy_robustness_v2_4.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
$p=".\runtime\real_market_multitimeframe_shadow\latest_1d_opposite_buy_robustness_v2_4.json"
if(-not(Test-Path $p)){throw "V2.4 RESULT MISSING"}
$r=Get-Content $p -Raw|ConvertFrom-Json
if($r.status -ne "PASS"){throw "V2.4 NOT PASS"}
if($r.interpretation_contract.production_change_applied -ne $false){throw "PRODUCTION CHANGE"}
if($r.contracts.broker_write_performed -ne $false){throw "BROKER WRITE"}
if($r.contracts.order_submission_performed -ne $false){throw "ORDER SUBMISSION"}
Write-Host ""
Write-Host "DEDUPLICATION STRESS:"
$r.deduplication_stress|ConvertTo-Json -Depth 10
Write-Host ""
Write-Host "ENTRY DELAY STRESS:"
$r.entry_delay_stress|ConvertTo-Json -Depth 10
Write-Host ""
Write-Host "COST STRESS:"
$r.round_trip_cost_stress_bps_on_45m|ConvertTo-Json -Depth 10
Write-Host ""
Write-Host "SYMBOL BREAKDOWN:"
$r.symbol_breakdown_45m|ConvertTo-Json -Depth 10
Write-Host ""
Write-Host "PATH EXCURSIONS:"
$r.path_excursions_45m|ConvertTo-Json -Depth 8
Write-Host ""
Write-Host "VERIFY: PASS"
