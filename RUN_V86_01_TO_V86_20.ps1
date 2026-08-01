$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v86_20\output"){Remove-Item "release\v86_20\output" -Recurse -Force}
python tools/install_check_v86_01_to_v86_20.py
python -m unittest tools.test_single_order_network_validation_v86_01_to_v86_20 -v
python tools/run_v86_01_to_v86_20_pipeline.py --repository-root . --clean
python tools/verify_v86_01_to_v86_20_pipeline.py --repository-root .
Write-Host "V86.01-V86.20 PASS - READY TO COMMIT"
