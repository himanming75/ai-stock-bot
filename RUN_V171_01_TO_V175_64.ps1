$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v171_01_to_v175_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
