$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python tools\run_v99_33_to_v99_64.py
if($LASTEXITCODE-ne 0){
    exit $LASTEXITCODE
}
