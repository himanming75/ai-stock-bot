$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v141_06_to_v141_08.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest tools.test_final_validation_release_bundle_v141_06_to_v141_08 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass -File .\RUN_V141_06_TO_V141_08_ULTRA_FAST.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools/verify_final_validation_release_bundle_v141_06_to_v141_08.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V141.06-V141.08 TEST AND VERIFY PASS"
