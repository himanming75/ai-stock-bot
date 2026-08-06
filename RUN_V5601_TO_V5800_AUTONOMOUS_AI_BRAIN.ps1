$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v5601_to_v5800_autonomous_ai_brain.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
