$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools\install_check_v88_17_to_v88_24.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest `
  tools.test_paper_production_release_v88_17_to_v88_24 `
  -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V88_17_TO_V88_24_PAPER_PRODUCTION_RELEASE.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools\verify_paper_production_release_v88_17_to_v88_24.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V88.17-V88.24 TEST AND VERIFY PASS"
