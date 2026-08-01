$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path "release\v117_00\output") {
    Remove-Item "release\v117_00\output" -Recurse -Force
}

Write-Host "=== V116.01-V117.00 INSTALL CHECK ==="
python tools/install_check_v116_01_to_v117_00.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V116.01-V117.00 REAL UNIT TESTS ==="
python -m unittest tools.test_paper_runtime_operational_stability_v116_01_to_v117_00 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V116.01-V117.00 OPERATIONAL STABILITY DEMO ==="
python tools/run_paper_runtime_operational_stability_v116_01_to_v117_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V116.01-V117.00 VERIFY ==="
python tools/verify_paper_runtime_operational_stability_v116_01_to_v117_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V116.01-V117.00 PAPER RUNTIME OPERATIONAL STABILITY PASS - READY TO COMMIT"
