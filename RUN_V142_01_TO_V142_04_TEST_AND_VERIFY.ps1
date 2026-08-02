$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v142_01_to_v142_04.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest tools.test_autonomous_paper_runtime_bundle_v142_01_to_v142_04 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass -File .\RUN_V142_01_TO_V142_04_ULTRA_FAST.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools/verify_autonomous_paper_runtime_bundle_v142_01_to_v142_04.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V142.01-V142.04 TEST AND VERIFY PASS"
