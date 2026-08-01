$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v83_20\output"){Remove-Item "release\v83_20\output" -Recurse -Force}
Write-Host "=== V83.01-V83.20 INSTALL CHECK ==="
python tools/install_check_v83_01_to_v83_20.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V83.01-V83.20 TESTS ==="
python -m unittest tools.test_paper_order_gate_v83_01_to_v83_20 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V83.01-V83.20 PIPELINE ==="
python tools/run_v83_01_to_v83_20_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V83.01-V83.20 VERIFY ==="
python tools/verify_v83_01_to_v83_20_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V83.01-V83.20 PASS - READY TO COMMIT"
