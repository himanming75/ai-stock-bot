$ErrorActionPreference="Stop"; Set-Location $PSScriptRoot
python tools\install_check_v89_01_to_v89_32.py; if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v89_01_to_v89_32 -v; if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V89_01_TO_V89_32.ps1; if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools\verify_v89_01_to_v89_32.py; if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V89.01-V89.32 TEST AND VERIFY PASS"
