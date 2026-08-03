$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V86.25-V86.32 AI EXPLAINABILITY ENGINE ==="
Write-Host "Local deterministic explanations only. No external AI API, network, broker write, or order submission."

python tools\run_ai_explainability_v86_25_to_v86_32.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V86.25-V86.32 COMPLETE"
