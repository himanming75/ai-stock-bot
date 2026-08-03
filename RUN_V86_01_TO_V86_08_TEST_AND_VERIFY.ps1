$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools\install_check_v86_01_to_v86_08.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest `
  tools.test_strategy_engine_v2_v86_01_to_v86_08 `
  -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V86_01_TO_V86_08_STRATEGY_ENGINE_V2.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools\verify_strategy_engine_v2_v86_01_to_v86_08.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V86.01-V86.08 TEST AND VERIFY PASS"
