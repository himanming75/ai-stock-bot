$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v83_73_to_v83_76.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest `
  tools.test_paper_autonomous_mode_v83_73_to_v83_76 `
  -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V83_73_TO_V83_76_PAPER_AUTONOMOUS_MODE.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools\verify_paper_autonomous_mode_v83_73_to_v83_76.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V83.73-V83.76 TEST AND VERIFY PASS"
