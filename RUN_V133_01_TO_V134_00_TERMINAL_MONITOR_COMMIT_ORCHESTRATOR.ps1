$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v134_00\output"){Remove-Item "release\v134_00\output" -Recurse -Force}
if(Test-Path "release\v134_00\ledger"){Remove-Item "release\v134_00\ledger" -Recurse -Force}
if(Test-Path "release\v134_00\recovery"){Remove-Item "release\v134_00\recovery" -Recurse -Force}
Write-Host "=== V133.01-V134.00 INSTALL CHECK ==="
python tools/install_check_v133_01_to_v134_00.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V133.01-V134.00 REAL UNIT TESTS ==="
python -m unittest tools.test_terminal_monitor_commit_orchestrator_v133_01_to_v134_00 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V133.01-V134.00 ORCHESTRATOR DEMO ==="
python tools/run_terminal_monitor_commit_orchestrator_v133_01_to_v134_00.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V133.01-V134.00 VERIFY ==="
python tools/verify_terminal_monitor_commit_orchestrator_v133_01_to_v134_00.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V133.01-V134.00 TERMINAL MONITOR COMMIT ORCHESTRATOR PASS - READY TO COMMIT"
