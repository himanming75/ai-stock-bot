param(
    [switch]$StartPilot
)
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

Write-Host "=== OP4.01-OP4.04 CONTROLLED PAPER PILOT ==="
Write-Host "Local pilot foundation only. No broker writes or automatic orders."

$argsList=@(
    "tools/run_controlled_paper_pilot_op4_01_to_op4_04.py",
    "--repository-root",
    "."
)
if($StartPilot){
    $argsList+="--start-pilot"
}

python @argsList
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "OP4.01-OP4.04 COMPLETE"
