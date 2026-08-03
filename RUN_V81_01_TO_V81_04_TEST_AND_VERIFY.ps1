$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/install_check_v81_01_to_v81_04.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_shadow_trading_foundation_v81_01_to_v81_04 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V81_01_TO_V81_04_SHADOW_FOUNDATION.ps1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/verify_shadow_trading_foundation_v81_01_to_v81_04.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V81.01-V81.04 TEST AND VERIFY PASS"
