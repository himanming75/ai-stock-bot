$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$OutputDir = Join-Path $PSScriptRoot "release\v79_60\output"
if (Test-Path $OutputDir) { Remove-Item $OutputDir -Recurse -Force }
Write-Host "=== V79.56-V79.60 INSTALL CHECK ==="
python tools/install_check_v79_56_to_v79_60.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V79.56-V79.60 TESTS ==="
python -m unittest tools.test_dataset_backup_restore_v79_56_to_v79_60 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V79.56-V79.60 PIPELINE ==="
python tools/run_v79_56_to_v79_60_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V79.56-V79.60 VERIFY ==="
python tools/verify_v79_56_to_v79_60_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.56-V79.60 PASS - READY TO COMMIT"
