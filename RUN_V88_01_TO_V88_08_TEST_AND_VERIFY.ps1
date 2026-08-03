$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools\install_check_v88_01_to_v88_08.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest `
  tools.test_web_ui_v2_v88_01_to_v88_08 `
  -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools\export_web_ui_v2_state.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools\verify_web_ui_v2_v88_01_to_v88_08.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V88.01-V88.08 TEST AND VERIFY PASS"
