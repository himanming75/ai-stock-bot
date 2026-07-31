$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$OutputDir = Join-Path $PSScriptRoot "release\v79_30\output"
if (Test-Path $OutputDir) {
    Write-Host "=== CLEARING STALE V79.30 OUTPUT ==="
    Remove-Item $OutputDir -Recurse -Force
}
Write-Host "=== V79.26-V79.30 INSTALL CHECK ==="
python tools/install_check_v79_26_to_v79_30.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V79.26-V79.30 TESTS ==="
python -m unittest tools.test_incremental_sync_v79_26_to_v79_30 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V79.26-V79.30 PIPELINE ==="
python tools/run_v79_26_to_v79_30_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V79.26-V79.30 VERIFY ==="
python tools/verify_v79_26_to_v79_30_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.26-V79.30 PASS - READY TO COMMIT"
