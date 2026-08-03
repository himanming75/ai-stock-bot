param([string]$SimulationDate="")
$ErrorActionPreference="Stop";Set-Location $PSScriptRoot
$argsList=@();if($SimulationDate){$argsList+="--simulation-date";$argsList+=$SimulationDate}
python tools\run_v95_01_to_v95_32.py @argsList
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
