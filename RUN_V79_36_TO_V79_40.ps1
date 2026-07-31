$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$OutputDir = Join-Path $PSScriptRoot "release\v79_40\output"
if (Test-Path $OutputDir) {
    Write-Host "=== CLEARING STALE V79.40 OUTPUT ==="
    Remove-Item $OutputDir -Recurse -Force
}
Write-Host "=== V79.36-V79.40 INSTALL CHECK ==="
python tools/install_check_v79_36_to_v79_40.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V79.36-V79.40 TESTS ==="
python -m unittest tools.test_quality_reconciliation_v79_36_to_v79_40 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V79.36-V79.40 PIPELINE ==="
python tools/run_v79_36_to_v79_40_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V79.36-V79.40 VERIFY ==="
python tools/verify_v79_36_to_v79_40_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.36-V79.40 PASS - READY TO COMMIT"
