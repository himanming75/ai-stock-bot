$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v1601_to_v1800_fundamental_sector_options.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
