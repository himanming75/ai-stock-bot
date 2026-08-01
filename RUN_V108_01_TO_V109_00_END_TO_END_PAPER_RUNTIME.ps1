$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path "release\v109_00\output") {
    Remove-Item "release\v109_00\output" -Recurse -Force
}

Write-Host "=== V108.01-V109.00 INSTALL CHECK ==="
python tools/install_check_v108_01_to_v109_00.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V108.01-V109.00 REAL UNIT TESTS ==="
python -m unittest tools.test_end_to_end_paper_runtime_v108_01_to_v109_00 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V108.01-V109.00 END-TO-END RUNTIME DEMO ==="
python tools/run_end_to_end_paper_runtime_v108_01_to_v109_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V108.01-V109.00 VERIFY ==="
python tools/verify_end_to_end_paper_runtime_v108_01_to_v109_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V108.01-V109.00 REAL END-TO-END PAPER RUNTIME PASS - READY TO COMMIT"
