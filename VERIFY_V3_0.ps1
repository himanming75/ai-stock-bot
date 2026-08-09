$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}

& $Python -m unittest .\tests\test_two_week_paper_validation_v3_0.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

$p=".\runtime\paper_2week_validation_v3_0\latest_validation_report.json"
if(-not(Test-Path $p)){throw "V3.0 REPORT MISSING"}

$r=Get-Content $p -Raw|ConvertFrom-Json

if($r.status -like "BLOCKED*"){throw "V3.0 BLOCKED: $($r.status)"}
if($r.contracts.duplicate_trading_engine_created -ne $false){throw "DUPLICATE ENGINE"}
if($r.contracts.paper_runtime_modified -ne $false){throw "PAPER RUNTIME MODIFIED"}
if($r.contracts.broker_write_performed_by_v3_0 -ne $false){throw "BROKER WRITE"}
if($r.contracts.paper_order_submission_performed_by_v3_0 -ne $false){throw "PAPER ORDER"}
if($r.contracts.live_order_submission_performed_by_v3_0 -ne $false){throw "LIVE ORDER"}
if($r.contracts.automatic_promotion -ne $false){throw "AUTO PROMOTION"}

Write-Host ""
Write-Host "V3.0 STATUS:"
$r.status

Write-Host ""
Write-Host "RUNTIME GATE:"
$r.runtime_gate|ConvertTo-Json -Depth 10

Write-Host ""
Write-Host "TWO-WEEK VALIDATION:"
$r.validation_state|ConvertTo-Json -Depth 10

Write-Host ""
Write-Host "HOOK INTEGRITY:"
$r.hook_integrity|ConvertTo-Json -Depth 10

Write-Host ""
Write-Host "VERIFY: PASS"
