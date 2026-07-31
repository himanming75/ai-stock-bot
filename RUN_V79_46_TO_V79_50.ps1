$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$OutputDir = Join-Path $PSScriptRoot "release\v79_50\output"
if (Test-Path $OutputDir) {
    Write-Host "=== CLEARING STALE V79.50 OUTPUT ==="
    Remove-Item $OutputDir -Recurse -Force
}
Write-Host "=== V79.46-V79.50 INSTALL CHECK ==="
python tools/install_check_v79_46_to_v79_50.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V79.46-V79.50 TESTS ==="
python -m unittest tools.test_dataset_retention_v79_46_to_v79_50 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V79.46-V79.50 PIPELINE ==="
python tools/run_v79_46_to_v79_50_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V79.46-V79.50 VERIFY ==="
python tools/verify_v79_46_to_v79_50_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.46-V79.50 PASS - READY TO COMMIT"
