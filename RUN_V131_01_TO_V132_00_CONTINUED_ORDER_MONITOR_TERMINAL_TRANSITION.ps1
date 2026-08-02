$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v132_00\output"){Remove-Item "release\v132_00\output" -Recurse -Force}
if(Test-Path "release\v132_00\ledger"){Remove-Item "release\v132_00\ledger" -Recurse -Force}
Write-Host "=== V131.01-V132.00 INSTALL CHECK ==="
python tools/install_check_v131_01_to_v132_00.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V131.01-V132.00 REAL UNIT TESTS ==="
python -m unittest tools.test_continued_actual_order_monitor_terminal_transition_v131_01_to_v132_00 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V131.01-V132.00 MONITOR/TERMINAL GATE DEMO ==="
python tools/run_continued_order_monitor_terminal_transition_v131_01_to_v132_00.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V131.01-V132.00 VERIFY ==="
python tools/verify_continued_order_monitor_terminal_transition_v131_01_to_v132_00.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V131.01-V132.00 CONTINUED ORDER MONITOR TERMINAL TRANSITION PASS - READY TO COMMIT"
