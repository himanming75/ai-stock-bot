param([Parameter(Mandatory=$true)][string]$Job)
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v191_01_to_v195_64.py --job $Job
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
