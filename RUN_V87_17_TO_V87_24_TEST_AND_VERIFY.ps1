$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools\install_check_v87_17_to_v87_24.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest `
  tools.test_multi_asset_backtest_v87_17_to_v87_24 `
  -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V87_17_TO_V87_24_MULTI_ASSET_BACKTEST.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools\verify_multi_asset_backtest_v87_17_to_v87_24.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V87.17-V87.24 TEST AND VERIFY PASS"
