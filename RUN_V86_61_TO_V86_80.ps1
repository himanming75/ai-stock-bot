$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v86_80\output"){Remove-Item "release\v86_80\output" -Recurse -Force}
Write-Host "=== V86.61-V86.80 INSTALL CHECK ==="
python tools/install_check_v86_61_to_v86_80.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V86.61-V86.80 TESTS ==="
python -m unittest tools.test_final_network_certification_v86_61_to_v86_80 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V86.61-V86.80 PIPELINE ==="
python tools/run_v86_61_to_v86_80_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V86.61-V86.80 VERIFY ==="
python tools/verify_v86_61_to_v86_80_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V86.61-V86.80 PASS - READY TO COMMIT"
