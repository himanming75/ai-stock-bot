$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
Write-Host "=== V139.11-V139.15 ULTRA FAST CYCLE FINALIZATION ==="
Write-Host "Local reconciliation, settlement, ledger, archive, and bootstrap only."
python tools/run_ultra_fast_cycle_finalization_v139_11_to_v139_15.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V139.11-V139.15 ULTRA FAST CYCLE FINALIZATION COMPLETE"
