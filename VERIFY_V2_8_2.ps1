$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}

& $Python -m unittest .\tests\test_repair_exact_paper_loop_shadow_v2_8_2.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python -m py_compile .\paper_daily_session\runner.py
if($LASTEXITCODE -ne 0){throw "RUNNER COMPILE FAILED"}

$p=".\runtime\regime_aware_buy_shadow_v2_8_2\latest_repair_v2_8_2.json"
if(-not(Test-Path $p)){throw "V2.8.2 REPORT MISSING"}
$r=Get-Content $p -Raw|ConvertFrom-Json

if($r.status -ne "PASS_REPAIRED_AND_INTEGRATED"){throw "V2.8.2 NOT PASS"}
if($r.restored_from_backup -ne $true){throw "BACKUP RESTORE NOT CONFIRMED"}
if($r.compile_after_repair -ne $true){throw "COMPILE NOT CONFIRMED"}
if($r.method_marker_count -ne 1){throw "METHOD MARKER COUNT INVALID"}
if($r.call_marker_count -ne 1){throw "CALL MARKER COUNT INVALID"}
if($r.contracts.broker_write_added -ne $false){throw "BROKER WRITE ADDED"}
if($r.contracts.paper_order_submission_added -ne $false){throw "PAPER ORDER ADDED"}
if($r.contracts.live_order_submission_added -ne $false){throw "LIVE ORDER ADDED"}

Write-Host ""
Write-Host "REPAIR REPORT:"
$r|ConvertTo-Json -Depth 12

Write-Host ""
Write-Host "PATCH MARKERS:"
Select-String -Path .\paper_daily_session\runner.py -Pattern "_run_regime_shadow_cycle|regime_shadow_v2_8_1" | ForEach-Object { $_.Line }

Write-Host ""
Write-Host "VERIFY: PASS"
