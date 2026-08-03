$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools\install_check_v85_01_to_v85_08.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest `
  tools.test_dashboard_v2_v85_01_to_v85_08 `
  -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools\export_dashboard_v2_state.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools\verify_dashboard_v2_v85_01_to_v85_08.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V85.01-V85.08 TEST AND VERIFY PASS"
