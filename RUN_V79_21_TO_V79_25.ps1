$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$OutputDir = Join-Path $PSScriptRoot "release\v79_25\output"
if (Test-Path $OutputDir) {
    Write-Host "=== CLEARING STALE V79.25 OUTPUT ==="
    Remove-Item $OutputDir -Recurse -Force
}
Write-Host "=== V79.21-V79.25 INSTALL CHECK ==="
python tools/install_check_v79_21_to_v79_25.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V79.21-V79.25 TESTS ==="
python -m unittest tools.test_historical_ingestion_v79_21_to_v79_25 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V79.21-V79.25 PIPELINE ==="
python tools/run_v79_21_to_v79_25_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V79.21-V79.25 VERIFY ==="
python tools/verify_v79_21_to_v79_25_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.21-V79.25 PASS - READY TO COMMIT"
