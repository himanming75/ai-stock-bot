$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path "release\v108_00\output") {
    Remove-Item "release\v108_00\output" -Recurse -Force
}

Write-Host "=== V107.01-V108.00 INSTALL CHECK ==="
python tools/install_check_v107_01_to_v108_00.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V107.01-V108.00 REAL UNIT TESTS ==="
python -m unittest tools.test_runtime_risk_manager_v107_01_to_v108_00 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V107.01-V108.00 RISK MANAGER DEMO ==="
python tools/run_runtime_risk_manager_v107_01_to_v108_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V107.01-V108.00 VERIFY ==="
python tools/verify_runtime_risk_manager_v107_01_to_v108_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V107.01-V108.00 REAL RUNTIME RISK MANAGER PASS - READY TO COMMIT"
