$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
Write-Host "=== V81.05-V81.08 SHADOW EXECUTION ENGINE ==="
Write-Host "Virtual orders and fills only. No broker requests or orders."
python tools/run_shadow_execution_v81_05_to_v81_08.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V81.05-V81.08 COMPLETE"
