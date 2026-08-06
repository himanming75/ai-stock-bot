$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v6401_to_v6600_autonomous_operations.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
