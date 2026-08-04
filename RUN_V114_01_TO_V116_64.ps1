$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v114_01_to_v116_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
