$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
Write-Host "=== V81.01-V81.04 READ-ONLY SHADOW TRADING FOUNDATION ==="
Write-Host "No broker writes, no order submission, and no position changes."
python tools/run_shadow_trading_foundation_v81_01_to_v81_04.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V81.01-V81.04 COMPLETE"
