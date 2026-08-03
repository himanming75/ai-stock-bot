$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python tools\run_v97_33_to_v97_64.py
if($LASTEXITCODE-ne 0){
    exit $LASTEXITCODE
}
