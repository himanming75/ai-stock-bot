$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V142.01-V142.04 AUTONOMOUS PAPER RUNTIME ==="
Write-Host "Local single-tick runtime only. No broker network, no order submission, no unbounded loop."

python tools/run_autonomous_paper_runtime_bundle_v142_01_to_v142_04.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V142.01-V142.04 COMPLETE"
