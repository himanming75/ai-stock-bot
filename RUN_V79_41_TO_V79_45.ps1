$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$OutputDir = Join-Path $PSScriptRoot "release\v79_45\output"
if (Test-Path $OutputDir) {
    Write-Host "=== CLEARING STALE V79.45 OUTPUT ==="
    Remove-Item $OutputDir -Recurse -Force
}
Write-Host "=== V79.41-V79.45 INSTALL CHECK ==="
python tools/install_check_v79_41_to_v79_45.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V79.41-V79.45 TESTS ==="
python -m unittest tools.test_dataset_versioning_v79_41_to_v79_45 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V79.41-V79.45 PIPELINE ==="
python tools/run_v79_41_to_v79_45_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V79.41-V79.45 VERIFY ==="
python tools/verify_v79_41_to_v79_45_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.41-V79.45 PASS - READY TO COMMIT"
