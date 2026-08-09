$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}

& $Python -m unittest .\tests\test_cleanup_git_check_repair_v2_9_1.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python -m py_compile .\paper_daily_session\runner.py
if($LASTEXITCODE -ne 0){throw "RUNNER COMPILE FAILED"}

$p=".\runtime\regime_aware_buy_shadow_v2_9\latest_runtime_shadow_certification_v2_9.json"
if(-not(Test-Path $p)){throw "V2.9 CERTIFICATION REPORT MISSING"}
$r=Get-Content $p -Raw|ConvertFrom-Json

if($r.status -like "BLOCKED*"){throw "V2.9 CERTIFICATION BLOCKED: $($r.status)"}
if($r.runner_integrity.method_marker_count -ne 1){throw "METHOD MARKER INVALID"}
if($r.runner_integrity.call_marker_count -ne 1){throw "CALL MARKER INVALID"}
if($r.certification_rules.structural_integrity_pass -ne $true){throw "STRUCTURAL INTEGRITY FAILED"}

Write-Host ""
Write-Host "CERTIFICATION STATUS:"
$r.status

Write-Host ""
Write-Host "HOOK OBSERVATION:"
$r.hook_observation|ConvertTo-Json -Depth 10

Write-Host ""
Write-Host "SHADOW LEDGER:"
$r.shadow_ledger|ConvertTo-Json -Depth 10

Write-Host ""
Write-Host "PAPER SESSION OBSERVATION:"
$r.paper_session_observation|ConvertTo-Json -Depth 10

Write-Host ""
Write-Host "VERIFY: PASS"
