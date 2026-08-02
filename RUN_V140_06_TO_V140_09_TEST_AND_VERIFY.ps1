$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/install_check_v140_06_to_v140_09.py
if ($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_autonomous_engine_bundle_v140_06_to_v140_09 -v
if ($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V140_06_TO_V140_09_ULTRA_FAST.ps1
if ($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/verify_autonomous_engine_bundle_v140_06_to_v140_09.py
if ($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V140.06-V140.09 TEST AND VERIFY PASS"
