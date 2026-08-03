
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v82_17_to_v82_20.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

python -m unittest `
  tools.test_shadow_trade_authorization_v82_17_to_v82_20 `
  -v
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V82_17_TO_V82_20_SHADOW_TRADE_AUTHORIZATION.ps1
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

python tools/verify_shadow_trade_authorization_v82_17_to_v82_20.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "V82.17-V82.20 TEST AND VERIFY PASS"
