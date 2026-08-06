$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v6201_to_v6400_autonomous_self_learning.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
