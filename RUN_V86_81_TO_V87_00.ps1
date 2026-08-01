$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v87_00\output"){Remove-Item "release\v87_00\output" -Recurse -Force}
Write-Host "=== V86.81-V87.00 INSTALL CHECK ==="
python tools/install_check_v86_81_to_v87_00.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V86.81-V87.00 TESTS ==="
python -m unittest tools.test_paper_broker_operations_v86_81_to_v87_00 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V86.81-V87.00 PIPELINE ==="
python tools/run_v86_81_to_v87_00_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V86.81-V87.00 VERIFY ==="
python tools/verify_v86_81_to_v87_00_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V86.81-V87.00 PASS - READY TO COMMIT"
