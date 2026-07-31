$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$OutputDir = Join-Path $PSScriptRoot "release\v79_35\output"
if (Test-Path $OutputDir) {
    Write-Host "=== CLEARING STALE V79.35 OUTPUT ==="
    Remove-Item $OutputDir -Recurse -Force
}
Write-Host "=== V79.31-V79.35 INSTALL CHECK ==="
python tools/install_check_v79_31_to_v79_35.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V79.31-V79.35 TESTS ==="
python -m unittest tools.test_gap_fill_v79_31_to_v79_35 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V79.31-V79.35 PIPELINE ==="
python tools/run_v79_31_to_v79_35_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V79.31-V79.35 VERIFY ==="
python tools/verify_v79_31_to_v79_35_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.31-V79.35 PASS - READY TO COMMIT"
