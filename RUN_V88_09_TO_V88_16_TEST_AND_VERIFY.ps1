$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools\install_check_v88_09_to_v88_16.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest `
  tools.test_paper_orchestrator_v88_09_to_v88_16 `
  -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V88_09_TO_V88_16_PAPER_ORCHESTRATOR.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools\verify_paper_orchestrator_v88_09_to_v88_16.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V88.09-V88.16 TEST AND VERIFY PASS"
