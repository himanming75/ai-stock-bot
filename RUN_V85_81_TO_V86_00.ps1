$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v86_00\output"){Remove-Item "release\v86_00\output" -Recurse -Force}
Write-Host "=== V85.81-V86.00 INSTALL CHECK ==="
python tools/install_check_v85_81_to_v86_00.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V85.81-V86.00 TESTS ==="
python -m unittest tools.test_paper_network_enablement_v85_81_to_v86_00 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V85.81-V86.00 PIPELINE ==="
python tools/run_v85_81_to_v86_00_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V85.81-V86.00 VERIFY ==="
python tools/verify_v85_81_to_v86_00_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V85.81-V86.00 PASS - READY TO COMMIT"
