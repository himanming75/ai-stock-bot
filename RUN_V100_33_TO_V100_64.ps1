$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python tools\run_v100_33_to_v100_64.py
if($LASTEXITCODE-ne 0){
    exit $LASTEXITCODE
}
