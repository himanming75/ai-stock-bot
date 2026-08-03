$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v81_09_to_v81_12.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

python -m unittest `
  tools.test_shadow_portfolio_v81_09_to_v81_12 `
  -v
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V81_09_TO_V81_12_SHADOW_PORTFOLIO.ps1
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

python tools/verify_shadow_portfolio_v81_09_to_v81_12.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "V81.09-V81.12 TEST AND VERIFY PASS"
