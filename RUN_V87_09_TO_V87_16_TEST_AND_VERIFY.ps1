$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools\install_check_v87_09_to_v87_16.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest `
  tools.test_walk_forward_stress_v87_09_to_v87_16 `
  -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V87_09_TO_V87_16_WALK_FORWARD_STRESS.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools\verify_walk_forward_stress_v87_09_to_v87_16.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V87.09-V87.16 TEST AND VERIFY PASS"
