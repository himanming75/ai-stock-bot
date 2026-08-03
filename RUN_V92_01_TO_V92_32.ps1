$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python tools\run_v92_01_to_v92_32.py
if($LASTEXITCODE-ne 0){
    exit $LASTEXITCODE
}
