$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V141.06-V141.08 FINAL VALIDATION AND PAPER RELEASE ==="
Write-Host "Local validation evidence and release generation only. No broker network or orders."

python tools/run_final_validation_release_bundle_v141_06_to_v141_08.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V141.06-V141.08 COMPLETE"
