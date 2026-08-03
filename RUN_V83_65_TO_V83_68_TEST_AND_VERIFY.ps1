$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v83_65_to_v83_68.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest `
  tools.test_end_to_end_paper_cycle_certification_v83_65_to_v83_68 `
  -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V83_65_TO_V83_68_END_TO_END_PAPER_CYCLE_CERTIFICATION.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools\verify_end_to_end_paper_cycle_certification_v83_65_to_v83_68.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V83.65-V83.68 TEST AND VERIFY PASS"
