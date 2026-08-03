$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools\install_check_v86_17_to_v86_24.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest `
  tools.test_portfolio_scoring_v86_17_to_v86_24 `
  -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V86_17_TO_V86_24_PORTFOLIO_SCORING.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools\verify_portfolio_scoring_v86_17_to_v86_24.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V86.17-V86.24 TEST AND VERIFY PASS"
