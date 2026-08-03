
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v82_29_to_v82_32.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

python -m unittest `
  tools.test_intraday_loop_v82_29_to_v82_32 `
  -v
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V82_29_TO_V82_32_INTRADAY_LOOP.ps1
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

python tools/verify_intraday_loop_v82_29_to_v82_32.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "V82.29-V82.32 TEST AND VERIFY PASS"
