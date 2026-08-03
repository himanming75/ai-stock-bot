$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V88.17-V88.24 PAPER PRODUCTION RELEASE ==="
Write-Host "Release gate only. No network, credentials, broker write, or order submission."

python tools\run_paper_production_release_v88_17_to_v88_24.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V88.17-V88.24 COMPLETE"
