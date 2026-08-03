$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v83_69_to_v83_72.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest `
  tools.test_operator_control_center_v83_69_to_v83_72 `
  -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V83_69_TO_V83_72_OPERATOR_CONTROL_CENTER.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools\verify_operator_control_center_v83_69_to_v83_72.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V83.69-V83.72 TEST AND VERIFY PASS"
