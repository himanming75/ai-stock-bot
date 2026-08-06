$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v5801_to_v6000_autonomous_multi_ai.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
