$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v83_89_to_v83_96.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest `
  tools.test_performance_production_readiness_v83_89_to_v83_96 `
  -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V83_89_TO_V83_96_PERFORMANCE_READINESS.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools/verify_performance_production_readiness_v83_89_to_v83_96.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V83.89-V83.96 TEST AND VERIFY PASS"
