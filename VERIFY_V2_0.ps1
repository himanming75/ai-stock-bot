$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}
& $Python -m unittest .\tests\test_buy_rejection_funnel_v2_0.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
$p=".\runtime\real_market_multitimeframe_shadow\latest_buy_rejection_funnel_v2_0.json"
if(-not(Test-Path $p)){throw "V2.0 RESULT MISSING"}
$r=Get-Content $p -Raw|ConvertFrom-Json
if($r.status -ne "PASS"){throw "V2.0 NOT PASS"}
if($r.interpretation_contract.production_change_applied -ne $false){throw "PRODUCTION CHANGE APPLIED"}
if($r.contracts.broker_write_performed -ne $false){throw "BROKER WRITE"}
if($r.contracts.order_submission_performed -ne $false){throw "ORDER SUBMISSION"}
Write-Host ""
Write-Host "BUY FUNNEL:"
$r.buy_funnel|ConvertTo-Json -Depth 8
Write-Host ""
Write-Host "REWARD/RISK DIAGNOSTICS:"
$r.reward_risk_diagnostics|ConvertTo-Json -Depth 8
Write-Host ""
Write-Host "CONFIDENCE DIAGNOSTICS:"
$r.confidence_diagnostics|ConvertTo-Json -Depth 8
Write-Host ""
Write-Host "RANKING LOSS DIAGNOSTICS:"
$r.ranking_loss_diagnostics|Select-Object count,median_confidence_gap_to_sell_winner,max_confidence_gap_to_sell_winner,median_rr_gap_to_sell_winner|ConvertTo-Json
Write-Host ""
Write-Host "CHECKPOINT SUMMARY:"
$r.checkpoint_summary|ConvertTo-Json
Write-Host ""
Write-Host "VERIFY: PASS"
