$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$OutputDir = Join-Path $PSScriptRoot "release\v79_55\output"
if (Test-Path $OutputDir) { Remove-Item $OutputDir -Recurse -Force }
Write-Host "=== V79.51-V79.55 INSTALL CHECK ==="
python tools/install_check_v79_51_to_v79_55.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V79.51-V79.55 TESTS ==="
python -m unittest tools.test_dataset_recovery_v79_51_to_v79_55 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V79.51-V79.55 PIPELINE ==="
python tools/run_v79_51_to_v79_55_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V79.51-V79.55 VERIFY ==="
python tools/verify_v79_51_to_v79_55_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.51-V79.55 PASS - READY TO COMMIT"
