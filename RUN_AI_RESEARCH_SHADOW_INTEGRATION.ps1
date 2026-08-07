$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
$Python=Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $Python .\tools\run_ai_research_shadow_integration.py --root $PSScriptRoot
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
