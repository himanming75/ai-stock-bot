$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v95_00\output"){Remove-Item "release\v95_00\output" -Recurse -Force}
Write-Host "=== V94.01-V95.00 FAST TRACK INSTALL CHECK ==="
python tools/install_check_v94_01_to_v95_00_fast_track.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V94.01-V95.00 FAST TRACK TESTS ==="
python -m unittest tools.test_single_order_network_optin_fast_track_v94_01_to_v95_00 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V94.01-V95.00 FAST TRACK PIPELINE ==="
python tools/run_v94_01_to_v95_00_fast_track_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V94.01-V95.00 FAST TRACK VERIFY ==="
python tools/verify_v94_01_to_v95_00_fast_track.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V94.01-V95.00 FAST TRACK PASS - READY TO COMMIT"
