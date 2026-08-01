$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/install_check_v86_21_to_v86_40.py
python -m unittest tools.test_order_lifecycle_v86_21_to_v86_40 -v
python tools/run_v86_21_to_v86_40_pipeline.py --repository-root . --clean
python tools/verify_v86_21_to_v86_40_pipeline.py
Write-Host "V86.21-V86.40 PASS - READY TO COMMIT"
