$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v128_00\output"){Remove-Item "release\v128_00\output" -Recurse -Force}
Write-Host "=== V127.01-V128.00 INSTALL CHECK ==="
python tools/install_check_v127_01_to_v128_00.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V127.01-V128.00 REAL UNIT TESTS ==="
python -m unittest tools.test_existing_paper_order_lifecycle_v127_01_to_v128_00 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V127.01-V128.00 LIFECYCLE DEMO ==="
python tools/run_existing_paper_order_lifecycle_v127_01_to_v128_00.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V127.01-V128.00 VERIFY ==="
python tools/verify_existing_paper_order_lifecycle_v127_01_to_v128_00.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V127.01-V128.00 EXISTING PAPER ORDER LIFECYCLE PASS - READY TO COMMIT"
