
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v82_09_to_v82_12.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

python -m unittest `
  tools.test_shadow_performance_v82_09_to_v82_12 `
  -v
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V82_09_TO_V82_12_SHADOW_PERFORMANCE.ps1
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

python tools/verify_shadow_performance_v82_09_to_v82_12.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "V82.09-V82.12 TEST AND VERIFY PASS"
