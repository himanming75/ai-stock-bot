param([string]$InputPath="")
$ErrorActionPreference="Stop";Set-Location $PSScriptRoot
$argsList=@();if($InputPath){$argsList+="--input";$argsList+=$InputPath}
python tools\run_v91_01_to_v91_32.py @argsList
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
