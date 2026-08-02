param(
    [switch]$AuthorizeCycle
)
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

Write-Host "=== OP4.17-OP4.20 PAPER PILOT AUTOMATION FOUNDATION ==="
Write-Host "Single local cycle plan only. No network, broker writes, or orders."

$argsList=@(
    "tools/run_paper_pilot_automation_op4_17_to_op4_20.py",
    "--repository-root",
    "."
)
if($AuthorizeCycle){
    $argsList+="--authorize-cycle"
}

python @argsList
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "OP4.17-OP4.20 COMPLETE"
