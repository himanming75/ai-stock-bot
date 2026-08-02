$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/install_check_v140_02_to_v140_05.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python -m unittest tools.test_runtime_control_bundle_v140_02_to_v140_05 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
powershell -ExecutionPolicy Bypass -File .\RUN_V140_02_TO_V140_05_ULTRA_FAST.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_runtime_control_bundle_v140_02_to_v140_05.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V140.02-V140.05 TEST AND VERIFY PASS"
