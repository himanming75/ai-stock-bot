$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V81.09-V81.12 SHADOW PORTFOLIO AND PNL ==="
Write-Host "Local virtual portfolio only. No broker requests or orders."

python tools/run_shadow_portfolio_v81_09_to_v81_12.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "V81.09-V81.12 COMPLETE"
