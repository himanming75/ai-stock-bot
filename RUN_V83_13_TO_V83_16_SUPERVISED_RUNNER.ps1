
param([switch]$ExecuteRunner,[switch]$ClearRunnerLock)
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
Write-Host "=== V83.13-V83.16 SUPERVISED AUTOMATION RUNNER ==="
Write-Host "Bounded supervised cycles only. No broker orders."
$argsList=@()
if($ExecuteRunner){$argsList+="--execute-runner"}
if($ClearRunnerLock){$argsList+="--clear-runner-lock"}
python tools/run_supervised_automation_runner_v83_13_to_v83_16.py @argsList
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V83.13-V83.16 COMPLETE"
