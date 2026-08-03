$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools\install_check_v86_09_to_v86_16.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest `
  tools.test_indicator_engine_v86_09_to_v86_16 `
  -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V86_09_TO_V86_16_INDICATOR_ENGINE.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools\verify_indicator_engine_v86_09_to_v86_16.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V86.09-V86.16 TEST AND VERIFY PASS"
