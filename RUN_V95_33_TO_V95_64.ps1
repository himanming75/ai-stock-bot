param([string]$LifecycleDate="")
$ErrorActionPreference="Stop";Set-Location $PSScriptRoot
$argsList=@();if($LifecycleDate){$argsList+="--lifecycle-date";$argsList+=$LifecycleDate}
python tools\run_v95_33_to_v95_64.py @argsList
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
