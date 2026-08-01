$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v90_00\output"){Remove-Item "release\v90_00\output" -Recurse -Force}
Write-Host "=== V88.81-V90.00 FAST TRACK INSTALL CHECK ==="
python tools/install_check_v88_81_to_v90_00.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V88.81-V90.00 FAST TRACK TESTS ==="
python -m unittest tools.test_fast_track_v88_81_to_v90_00 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V88.81-V90.00 FAST TRACK PIPELINE ==="
python tools/run_v88_81_to_v90_00_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V88.81-V90.00 FAST TRACK VERIFY ==="
python tools/verify_v88_81_to_v90_00_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V88.81-V90.00 FAST TRACK PASS - READY TO COMMIT"
