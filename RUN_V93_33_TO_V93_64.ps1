param([string]$InputPath="")
$ErrorActionPreference="Stop";Set-Location $PSScriptRoot
$argsList=@();if($InputPath){$argsList+="--input";$argsList+=$InputPath}
python tools\run_v93_33_to_v93_64.py @argsList
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
