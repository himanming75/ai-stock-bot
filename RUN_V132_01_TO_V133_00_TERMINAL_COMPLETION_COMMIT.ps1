$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v133_00\output"){Remove-Item "release\v133_00\output" -Recurse -Force}
if(Test-Path "release\v133_00\ledger"){Remove-Item "release\v133_00\ledger" -Recurse -Force}
if(Test-Path "release\v133_00\recovery"){Remove-Item "release\v133_00\recovery" -Recurse -Force}

Write-Host "=== V132.01-V133.00 INSTALL CHECK ==="
python tools/install_check_v132_01_to_v133_00.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "=== V132.01-V133.00 REAL UNIT TESTS ==="
python -m unittest tools.test_terminal_completion_commit_v132_01_to_v133_00 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "=== V132.01-V133.00 TERMINAL COMMIT GATE ==="
python tools/run_terminal_completion_commit_v132_01_to_v133_00.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "=== V132.01-V133.00 VERIFY ==="
python tools/verify_terminal_completion_commit_v132_01_to_v133_00.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "V132.01-V133.00 TERMINAL COMPLETION COMMIT PASS - READY TO COMMIT"
