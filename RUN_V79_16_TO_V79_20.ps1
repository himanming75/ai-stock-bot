$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$OutputDir = Join-Path $PSScriptRoot "release\v79_20\output"
if (Test-Path $OutputDir) {
    Write-Host "=== CLEARING STALE V79.20 OUTPUT ==="
    Remove-Item $OutputDir -Recurse -Force
}
Write-Host "=== V79.16-V79.20 INSTALL CHECK ==="
python tools/install_check_v79_16_to_v79_20.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V79.16-V79.20 TESTS ==="
python -m unittest tools.test_network_smoke_v79_16_to_v79_20 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V79.16-V79.20 SAFE PIPELINE ==="
python tools/run_v79_16_to_v79_20_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V79.16-V79.20 VERIFY ==="
python tools/verify_v79_16_to_v79_20_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.16-V79.20 PASS - READY TO COMMIT"
