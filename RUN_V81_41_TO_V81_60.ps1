$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v81_60\output"){Remove-Item "release\v81_60\output" -Recurse -Force}
Write-Host "=== V81.41-V81.60 INSTALL CHECK ==="
python tools/install_check_v81_41_to_v81_60.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V81.41-V81.60 TESTS ==="
python -m unittest tools.test_broker_adapter_foundation_v81_41_to_v81_60 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V81.41-V81.60 PIPELINE ==="
python tools/run_v81_41_to_v81_60_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V81.41-V81.60 VERIFY ==="
python tools/verify_v81_41_to_v81_60_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V81.41-V81.60 PASS - READY TO COMMIT"
