$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v96_00\output"){Remove-Item "release\v96_00\output" -Recurse -Force}
Write-Host "=== V95.01-V96.00 FAST TRACK INSTALL CHECK ==="
python tools/install_check_v95_01_to_v96_00_fast_track.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V95.01-V96.00 FAST TRACK TESTS ==="
python -m unittest tools.test_controlled_execution_fast_track_v95_01_to_v96_00 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V95.01-V96.00 FAST TRACK PIPELINE (OFFLINE DEFAULT) ==="
python tools/run_v95_01_to_v96_00_fast_track_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V95.01-V96.00 FAST TRACK VERIFY ==="
python tools/verify_v95_01_to_v96_00_fast_track.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V95.01-V96.00 FAST TRACK PASS - READY TO COMMIT"
