param([switch]$PrepareExecution,[switch]$ExecuteMode,[switch]$ClearExecutionLock,[string]$ObservedAt="")
$ErrorActionPreference="Stop"; Set-Location $PSScriptRoot
$argsList=@()
if($PrepareExecution){$argsList+="--prepare-execution"}
if($ExecuteMode){$argsList+="--execute-mode"}
if($ClearExecutionLock){$argsList+="--clear-execution-lock"}
if($ObservedAt){$argsList+="--observed-at";$argsList+=$ObservedAt}
python tools/run_reentry_execution_guard_audit_v83_45_to_v83_48.py @argsList
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
