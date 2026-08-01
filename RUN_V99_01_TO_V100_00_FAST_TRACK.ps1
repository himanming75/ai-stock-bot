$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v100_00\output"){Remove-Item "release\v100_00\output" -Recurse -Force}
Write-Host "=== V99.01-V100.00 FAST TRACK INSTALL CHECK ==="
python tools/install_check_v99_01_to_v100_00_fast_track.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V99.01-V100.00 FAST TRACK TESTS ==="
python -m unittest tools.test_final_production_candidate_fast_track_v99_01_to_v100_00 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V99.01-V100.00 FAST TRACK PIPELINE (OFFLINE DEFAULT) ==="
python tools/run_v99_01_to_v100_00_fast_track_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V99.01-V100.00 FAST TRACK VERIFY ==="
python tools/verify_v99_01_to_v100_00_fast_track.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V99.01-V100.00 FAST TRACK PASS - READY TO COMMIT"
