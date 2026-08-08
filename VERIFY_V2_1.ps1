$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}
& $Python -m unittest .\tests\test_buy_sell_rr_symmetry_v2_1.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
$p=".\runtime\real_market_multitimeframe_shadow\latest_buy_sell_rr_symmetry_v2_1.json"
if(-not(Test-Path $p)){throw "V2.1 RESULT MISSING"}
$r=Get-Content $p -Raw|ConvertFrom-Json
if($r.status -ne "PASS"){throw "V2.1 NOT PASS"}
if($r.comparison.formula_identity.formula_is_directionally_symmetric -ne $true){throw "RR FORMULA NOT SYMMETRIC"}
if($r.interpretation_contract.rr_formula_changed -ne $false){throw "RR FORMULA CHANGED"}
if($r.contracts.broker_write_performed -ne $false){throw "BROKER WRITE"}
if($r.contracts.order_submission_performed -ne $false){throw "ORDER SUBMISSION"}
Write-Host ""
Write-Host "BUY SUMMARY:"
$r.buy_summary|ConvertTo-Json -Depth 8
Write-Host ""
Write-Host "SELL SUMMARY:"
$r.sell_summary|ConvertTo-Json -Depth 8
Write-Host ""
Write-Host "BUY/SELL RATIOS:"
$r.comparison.buy_vs_sell_mean_ratios|ConvertTo-Json -Depth 8
Write-Host ""
Write-Host "FORMULA IDENTITY:"
$r.comparison.formula_identity|ConvertTo-Json -Depth 8
Write-Host ""
Write-Host "VERIFY: PASS"
