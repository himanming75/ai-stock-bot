$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v1801_to_v2000_unified_ai_decision.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
