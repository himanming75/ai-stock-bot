$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path "release\v119_00\output") {
    Remove-Item "release\v119_00\output" -Recurse -Force
}

Write-Host "=== V118.01-V119.00 INSTALL CHECK ==="
python tools/install_check_v118_01_to_v119_00.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V118.01-V119.00 REAL UNIT TESTS ==="
python -m unittest tools.test_continuous_paper_runtime_final_certification_v118_01_to_v119_00 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V118.01-V119.00 FINAL CERTIFICATION ==="
python tools/run_continuous_paper_runtime_final_certification_v118_01_to_v119_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V118.01-V119.00 VERIFY ==="
python tools/verify_continuous_paper_runtime_final_certification_v118_01_to_v119_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V118.01-V119.00 CONTINUOUS PAPER RUNTIME FINAL CERTIFICATION PASS - READY TO COMMIT"
