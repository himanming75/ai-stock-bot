$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v139_00\output"){Remove-Item "release\v139_00\output" -Recurse -Force}
if(Test-Path "release\v139_00\runtime"){Remove-Item "release\v139_00\runtime" -Recurse -Force}

Write-Host "=== V138.01-V139.00 INSTALL CHECK ==="
python tools/install_check_v138_01_to_v139_00.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "=== V138.01-V139.00 REAL UNIT TESTS ==="
python -m unittest tools.test_autonomous_cycle_continuation_v138_01_to_v139_00 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "=== V138.01-V139.00 CONTINUATION DEMO ==="
python tools/run_autonomous_cycle_continuation_v138_01_to_v139_00.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "=== V138.01-V139.00 VERIFY ==="
python tools/verify_autonomous_cycle_continuation_v138_01_to_v139_00.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "V138.01-V139.00 AUTONOMOUS CYCLE CONTINUATION PASS - READY TO COMMIT"
