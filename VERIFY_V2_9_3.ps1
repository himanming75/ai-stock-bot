$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}

& $Python -m unittest .\tests\test_stale_lock_safe_recovery_v2_9_3.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

$RecoveryPath=".\runtime\regime_aware_buy_shadow_v2_9_3\latest_stale_lock_recovery_v2_9_3.json"
if(-not(Test-Path $RecoveryPath)){throw "V2.9.3 RECOVERY REPORT MISSING"}
$Recovery=Get-Content $RecoveryPath -Raw|ConvertFrom-Json

if($Recovery.status -notlike "PASS*"){throw "V2.9.3 RECOVERY NOT PASS"}
if($Recovery.contracts.scheduled_task_modified -ne $false){throw "TASK MODIFIED"}
if($Recovery.contracts.paper_runtime_started -ne $false){throw "PAPER RUNTIME STARTED"}
if($Recovery.contracts.broker_write_performed -ne $false){throw "BROKER WRITE"}
if($Recovery.contracts.paper_order_submission_performed -ne $false){throw "PAPER ORDER"}
if($Recovery.contracts.live_order_submission_performed -ne $false){throw "LIVE ORDER"}

$AuditPath=".\runtime\regime_aware_buy_shadow_v2_9_2\latest_runtime_activation_audit_v2_9_2.json"
if(-not(Test-Path $AuditPath)){throw "V2.9.2 RE-AUDIT REPORT MISSING"}
$Audit=Get-Content $AuditPath -Raw|ConvertFrom-Json

if($Audit.status -like "BLOCKED*"){throw "READINESS STILL BLOCKED: $($Audit.status)"}
if($Audit.runtime_integrity.lock.exists -eq $true -and $Audit.runtime_integrity.lock.stale -eq $true){
    throw "STALE LOCK STILL PRESENT"
}
if($Audit.runtime_integrity.runner_compile_pass -ne $true){throw "RUNNER COMPILE FAILED"}
if($Audit.runtime_integrity.hook_method_count -ne 1){throw "HOOK METHOD INVALID"}
if($Audit.runtime_integrity.hook_call_count -ne 1){throw "HOOK CALL INVALID"}

Write-Host ""
Write-Host "RECOVERY REPORT:"
$Recovery|ConvertTo-Json -Depth 12

Write-Host ""
Write-Host "READINESS STATUS:"
$Audit.status

Write-Host ""
Write-Host "TASK SELECTION:"
$Audit.task_selection|ConvertTo-Json -Depth 12

Write-Host ""
Write-Host "RUNTIME INTEGRITY:"
$Audit.runtime_integrity|ConvertTo-Json -Depth 12

Write-Host ""
Write-Host "VERIFY: PASS"
