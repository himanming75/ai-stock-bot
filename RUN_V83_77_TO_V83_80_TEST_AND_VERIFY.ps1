$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v83_77_to_v83_80.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest `
  tools.test_multi_day_paper_validation_v83_77_to_v83_80 `
  -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V83_77_TO_V83_80_MULTI_DAY_PAPER_VALIDATION.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools/verify_multi_day_paper_validation_v83_77_to_v83_80.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V83.77-V83.80 TEST AND VERIFY PASS"
