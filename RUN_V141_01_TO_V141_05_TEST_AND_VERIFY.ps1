$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v141_01_to_v141_05.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest tools.test_operational_stability_bundle_v141_01_to_v141_05 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass -File .\RUN_V141_01_TO_V141_05_ULTRA_FAST.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools/verify_operational_stability_bundle_v141_01_to_v141_05.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V141.01-V141.05 TEST AND VERIFY PASS"
