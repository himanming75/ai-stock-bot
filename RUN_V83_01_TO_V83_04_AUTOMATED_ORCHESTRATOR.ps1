param([switch]$AuthorizeAction,[switch]$CompleteAction,[switch]$ClearActionLock)
$ErrorActionPreference='Stop'; Set-Location $PSScriptRoot
Write-Host '=== V83.01-V83.04 AUTOMATED PAPER ORCHESTRATOR ==='
Write-Host 'Decision and action planning only. No broker orders.'
$a=@(); if($AuthorizeAction){$a+='--authorize-action'}; if($CompleteAction){$a+='--complete-action'}; if($ClearActionLock){$a+='--clear-action-lock'}
python tools/run_automated_orchestrator_v83_01_to_v83_04.py @a
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host 'V83.01-V83.04 COMPLETE'
