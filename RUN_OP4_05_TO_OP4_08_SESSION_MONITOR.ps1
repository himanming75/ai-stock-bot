param(
    [switch]$WriteHeartbeat,
    [switch]$ControlledStop
)
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

Write-Host "=== OP4.05-OP4.08 PAPER SESSION MONITOR ==="
Write-Host "Local heartbeat and health monitoring only. No broker writes."

$argsList=@(
    "tools/run_paper_session_monitor_op4_05_to_op4_08.py",
    "--repository-root",
    "."
)
if($WriteHeartbeat){
    $argsList+="--write-heartbeat"
}
if($ControlledStop){
    $argsList+="--controlled-stop"
}

python @argsList
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "OP4.05-OP4.08 COMPLETE"
