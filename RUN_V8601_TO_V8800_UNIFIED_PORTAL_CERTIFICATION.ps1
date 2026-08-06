$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
  .\tools\run_v8601_to_v8800_unified_portal_certification.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
