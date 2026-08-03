$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python tools\run_v97_01_to_v97_32.py
if($LASTEXITCODE-ne 0){
    exit $LASTEXITCODE
}
