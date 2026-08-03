$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v89_33_to_v89_64.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
