$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}

& $Python -m unittest .\tests\test_regime_aware_shadow_v2_7.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

$p=".\runtime\regime_aware_buy_shadow_v2_7\latest_shadow_snapshot.json"
if(-not(Test-Path $p)){throw "V2.7 SNAPSHOT MISSING"}

$r=Get-Content $p -Raw|ConvertFrom-Json
if($r.status -ne "PASS"){throw "V2.7 NOT PASS"}
if($r.mode -ne "READ_ONLY_SHADOW"){throw "NOT READ-ONLY SHADOW"}
if($r.contracts.production_selector_modified -ne $false){throw "PRODUCTION SELECTOR MODIFIED"}
if($r.contracts.broker_write_performed -ne $false){throw "BROKER WRITE"}
if($r.contracts.paper_order_submission_performed -ne $false){throw "PAPER ORDER SUBMISSION"}
if($r.contracts.live_order_submission_performed -ne $false){throw "LIVE ORDER SUBMISSION"}

Write-Host ""
Write-Host "SHADOW SNAPSHOT:"
$r|Select-Object stage,status,mode,checkpoint_et,analysis_count,production_selected_candidate_observed_only,new_shadow_signals,new_shadow_outcomes|ConvertTo-Json -Depth 12

Write-Host ""
Write-Host "SAFETY CONTRACTS:"
$r.contracts|ConvertTo-Json -Depth 8

Write-Host ""
Write-Host "VERIFY: PASS"
