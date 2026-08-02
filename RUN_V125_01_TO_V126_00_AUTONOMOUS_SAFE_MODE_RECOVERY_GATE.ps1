$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path "release\v126_00\output") {
    Remove-Item "release\v126_00\output" -Recurse -Force
}

Write-Host "=== V125.01-V126.00 INSTALL CHECK ==="
python tools/install_check_v125_01_to_v126_00.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V125.01-V126.00 REAL UNIT TESTS ==="
python -m unittest tools.test_autonomous_safe_mode_recovery_gate_v125_01_to_v126_00 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V125.01-V126.00 READ-ONLY RECOVERY GATE ==="
python tools/run_autonomous_safe_mode_recovery_gate_v125_01_to_v126_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V125.01-V126.00 VERIFY ==="
python tools/verify_autonomous_safe_mode_recovery_gate_v125_01_to_v126_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V125.01-V126.00 AUTONOMOUS SAFE-MODE RECOVERY GATE PASS - READY TO COMMIT"
