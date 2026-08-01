$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path "release\v90_60\output") {
    Remove-Item "release\v90_60\output" -Recurse -Force
}

Write-Host "=== V90.41-V90.60 INSTALL CHECK ==="
python tools/install_check_v90_41_to_v90_60.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V90.41-V90.60 TESTS ==="
python -m unittest tools.test_actual_paper_runtime_certification_v90_41_to_v90_60 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V90.41-V90.60 PIPELINE ==="
python tools/run_v90_41_to_v90_60_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V90.41-V90.60 VERIFY ==="
python tools/verify_v90_41_to_v90_60_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V90.41-V90.60 PASS - READY TO COMMIT"
