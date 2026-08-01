$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (Test-Path "release\v79_95\output") {
    Remove-Item "release\v79_95\output" -Recurse -Force
}
python tools/install_check_v79_91_to_v79_95.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python -m unittest tools.test_historical_walk_forward_validation_v79_91_to_v79_95 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/run_v79_91_to_v79_95_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_v79_91_to_v79_95_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.91-V79.95 PASS - READY TO COMMIT"
