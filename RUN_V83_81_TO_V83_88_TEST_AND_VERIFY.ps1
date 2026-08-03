$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v83_81_to_v83_88.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest `
  tools.test_paper_stability_runtime_v83_81_to_v83_88 `
  -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V83_81_TO_V83_88_PAPER_STABILITY_RUNTIME.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools/verify_paper_stability_runtime_v83_81_to_v83_88.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V83.81-V83.88 TEST AND VERIFY PASS"
