$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path "release\v106_00\output") {
    Remove-Item "release\v106_00\output" -Recurse -Force
}

Write-Host "=== V105.01-V106.00 INSTALL CHECK ==="
python tools/install_check_v105_01_to_v106_00.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V105.01-V106.00 REAL UNIT TESTS ==="
python -m unittest tools.test_paper_execution_adapter_v105_01_to_v106_00 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V105.01-V106.00 MOCK PAPER EXECUTION DEMO ==="
python tools/run_paper_execution_adapter_v105_01_to_v106_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V105.01-V106.00 VERIFY ==="
python tools/verify_paper_execution_adapter_v105_01_to_v106_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V105.01-V106.00 REAL PAPER EXECUTION ADAPTER PASS - READY TO COMMIT"
