param([switch]$NoResume)
$ErrorActionPreference="Stop";Set-Location $PSScriptRoot
$argsList=@();if($NoResume){$argsList+="--no-resume"}
python tools\run_v98_33_to_v98_64.py @argsList
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
