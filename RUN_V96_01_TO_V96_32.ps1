$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python tools\run_v96_01_to_v96_32.py
if($LASTEXITCODE-ne 0){
    exit $LASTEXITCODE
}
