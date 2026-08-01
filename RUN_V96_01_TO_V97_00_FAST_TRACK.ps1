$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v97_00\output"){Remove-Item "release\v97_00\output" -Recurse -Force}
Write-Host "=== V96.01-V97.00 FAST TRACK INSTALL CHECK ==="
python tools/install_check_v96_01_to_v97_00_fast_track.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V96.01-V97.00 FAST TRACK TESTS ==="
python -m unittest tools.test_controlled_execution_validation_fast_track_v96_01_to_v97_00 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V96.01-V97.00 FAST TRACK PIPELINE (OFFLINE DEFAULT) ==="
python tools/run_v96_01_to_v97_00_fast_track_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V96.01-V97.00 FAST TRACK VERIFY ==="
python tools/verify_v96_01_to_v97_00_fast_track.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V96.01-V97.00 FAST TRACK PASS - READY TO COMMIT"
