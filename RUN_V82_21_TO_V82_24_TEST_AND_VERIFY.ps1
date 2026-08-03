
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v82_21_to_v82_24.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

python -m unittest `
  tools.test_paper_session_manager_v82_21_to_v82_24 `
  -v
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V82_21_TO_V82_24_PAPER_SESSION_MANAGER.ps1
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

python tools/verify_paper_session_manager_v82_21_to_v82_24.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "V82.21-V82.24 TEST AND VERIFY PASS"
