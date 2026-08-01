$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v94_00\output"){Remove-Item "release\v94_00\output" -Recurse -Force}
Write-Host "=== V93.01-V94.00 FAST TRACK INSTALL CHECK ==="
python tools/install_check_v93_01_to_v94_00_fast_track.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V93.01-V94.00 FAST TRACK TESTS ==="
python -m unittest tools.test_submission_enablement_fast_track_v93_01_to_v94_00 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V93.01-V94.00 FAST TRACK PIPELINE ==="
python tools/run_v93_01_to_v94_00_fast_track_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V93.01-V94.00 FAST TRACK VERIFY ==="
python tools/verify_v93_01_to_v94_00_fast_track.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V93.01-V94.00 FAST TRACK PASS - READY TO COMMIT"
