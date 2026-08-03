$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools\install_check_v87_01_to_v87_08.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest `
  tools.test_backtest_v2_v87_01_to_v87_08 `
  -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V87_01_TO_V87_08_BACKTEST_V2.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools\verify_backtest_v2_v87_01_to_v87_08.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V87.01-V87.08 TEST AND VERIFY PASS"
