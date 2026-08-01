$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path "release\v104_00\output") {
    Remove-Item "release\v104_00\output" -Recurse -Force
}

Write-Host "=== V103.01-V104.00 INSTALL CHECK ==="
python tools/install_check_v103_01_to_v104_00.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V103.01-V104.00 REAL UNIT TESTS ==="
python -m unittest tools.test_strategy_signal_engine_v103_01_to_v104_00 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V103.01-V104.00 SIGNAL ENGINE DEMO ==="
python tools/run_strategy_signal_engine_v103_01_to_v104_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V103.01-V104.00 VERIFY ==="
python tools/verify_strategy_signal_engine_v103_01_to_v104_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V103.01-V104.00 REAL STRATEGY SIGNAL ENGINE PASS - READY TO COMMIT"
