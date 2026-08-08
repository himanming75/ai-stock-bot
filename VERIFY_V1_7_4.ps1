$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}
& $Python -m unittest .\tests\test_v1_7_4_fast_holdout_audit.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
$p=".\runtime\real_market_multitimeframe_shadow\latest_holdout_zero_trade_audit_v1_7_4.json"
if(-not(Test-Path $p)){throw "AUDIT RESULT MISSING"}
$r=Get-Content $p -Raw|ConvertFrom-Json
if($r.status -ne "PASS"){throw "AUDIT NOT PASS"}
if($r.scope_summary.market_checkpoints -le 0){throw "ZERO CHECKPOINTS"}
if($r.canonical_reuse.duplicate_engine_created -ne $false){throw "DUPLICATE ENGINE"}
if($r.contracts.network_used_by_audit -ne $false){throw "AUDIT NETWORK USE"}
if($r.contracts.broker_write_performed -ne $false){throw "BROKER WRITE"}
if($r.contracts.order_submission_performed -ne $false){throw "ORDER SUBMISSION"}
Write-Host ""
Write-Host "ZERO-TRADE ROOT CAUSES:"
$r.scope_summary.zero_trade_day_root_cause_counts|ConvertTo-Json -Depth 8
Write-Host ""
Write-Host "ZERO-TRADE DATES:"
$r.scope_summary.zero_trade_date_list|ConvertTo-Json
Write-Host ""
Write-Host "VERIFY: PASS"
