$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v99_00\output"){Remove-Item "release\v99_00\output" -Recurse -Force}
Write-Host "=== V98.01-V99.00 FAST TRACK INSTALL CHECK ==="
python tools/install_check_v98_01_to_v99_00_fast_track.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V98.01-V99.00 FAST TRACK TESTS ==="
python -m unittest tools.test_multi_session_validation_fast_track_v98_01_to_v99_00 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V98.01-V99.00 FAST TRACK PIPELINE (OFFLINE DEFAULT) ==="
python tools/run_v98_01_to_v99_00_fast_track_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V98.01-V99.00 FAST TRACK VERIFY ==="
python tools/verify_v98_01_to_v99_00_fast_track.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V98.01-V99.00 FAST TRACK PASS - READY TO COMMIT"
