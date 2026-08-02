$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/install_check_v142_05_to_v142_08.py
if ($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_scheduled_runtime_bundle_v142_05_to_v142_08 -v
if ($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V142_05_TO_V142_08_ULTRA_FAST.ps1
if ($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/verify_scheduled_runtime_bundle_v142_05_to_v142_08.py
if ($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V142.05-V142.08 TEST AND VERIFY PASS"
