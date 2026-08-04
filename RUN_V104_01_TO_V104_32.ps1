$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v104_01_to_v104_32.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
