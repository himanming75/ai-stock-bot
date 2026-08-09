$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}

& $Python -m unittest .\tests\test_runtime_activation_audit_v2_9_2.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

$p=".\runtime\regime_aware_buy_shadow_v2_9_2\latest_runtime_activation_audit_v2_9_2.json"
if(-not(Test-Path $p)){throw "V2.9.2 REPORT MISSING"}

$r=Get-Content $p -Raw | ConvertFrom-Json

if($r.status -like "BLOCKED*"){throw "V2.9.2 BLOCKED: $($r.status)"}
if($r.runtime_integrity.runner_compile_pass -ne $true){throw "RUNNER COMPILE FAILED"}
if($r.runtime_integrity.hook_method_count -ne 1){throw "HOOK METHOD COUNT INVALID"}
if($r.runtime_integrity.hook_call_count -ne 1){throw "HOOK CALL COUNT INVALID"}
if($r.activation_contract.scheduled_task_modified -ne $false){throw "TASK MODIFIED"}
if($r.activation_contract.paper_runtime_started_by_v2_9_2 -ne $false){throw "PAPER RUNTIME STARTED"}
if($r.activation_contract.broker_write_performed -ne $false){throw "BROKER WRITE"}
if($r.activation_contract.paper_order_submission_performed -ne $false){throw "PAPER ORDER"}
if($r.activation_contract.live_order_submission_performed -ne $false){throw "LIVE ORDER"}

Write-Host ""
Write-Host "ACTIVATION STATUS:"
$r.status

Write-Host ""
Write-Host "TASK SELECTION:"
$r.task_selection | ConvertTo-Json -Depth 12

Write-Host ""
Write-Host "RUNTIME INTEGRITY:"
$r.runtime_integrity | ConvertTo-Json -Depth 12

Write-Host ""
Write-Host "ACTIVATION CONTRACT:"
$r.activation_contract | ConvertTo-Json -Depth 8

Write-Host ""
Write-Host "VERIFY: PASS"
