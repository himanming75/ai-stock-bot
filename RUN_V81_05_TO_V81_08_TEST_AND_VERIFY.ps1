$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/install_check_v81_05_to_v81_08.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_shadow_execution_v81_05_to_v81_08 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V81_05_TO_V81_08_SHADOW_EXECUTION.ps1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/verify_shadow_execution_v81_05_to_v81_08.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V81.05-V81.08 TEST AND VERIFY PASS"
