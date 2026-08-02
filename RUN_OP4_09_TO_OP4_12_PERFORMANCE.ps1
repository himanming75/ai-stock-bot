param(
    [switch]$CollectSnapshot
)
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

Write-Host "=== OP4.09-OP4.12 PAPER PERFORMANCE COLLECTOR ==="
Write-Host "Local performance collection only. No broker requests or orders."

$argsList=@(
    "tools/run_paper_performance_collector_op4_09_to_op4_12.py",
    "--repository-root",
    "."
)
if($CollectSnapshot){
    $argsList+="--collect-snapshot"
}

python @argsList
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "OP4.09-OP4.12 COMPLETE"
