$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$OutputDir = Join-Path $PSScriptRoot "release\v79_15\output"
if (Test-Path $OutputDir) { Write-Host "=== CLEARING STALE V79.15 OUTPUT ==="; Remove-Item $OutputDir -Recurse -Force }
Write-Host "=== V79.11-V79.15 INSTALL CHECK ==="
python tools/install_check_v79_11_to_v79_15.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V79.11-V79.15 TESTS ==="
python -m unittest tools.test_authenticated_gate_v79_11_to_v79_15 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V79.11-V79.15 PIPELINE ==="
python tools/run_v79_11_to_v79_15_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V79.11-V79.15 VERIFY ==="
python tools/verify_v79_11_to_v79_15_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.11-V79.15 PASS - READY TO COMMIT"
