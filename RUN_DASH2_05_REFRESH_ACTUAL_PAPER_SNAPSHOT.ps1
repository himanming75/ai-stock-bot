param(
    [switch]$EnableNetwork
)
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

Write-Host "=== DASH2.05 ACTUAL PAPER SNAPSHOT REFRESH ==="
Write-Host "Read-only GET: account, positions, open orders, and clock."

$argsList=@(
    "tools/run_current_paper_snapshot_collector_dash2_05.py",
    "--repository-root",
    "."
)
if($EnableNetwork){
    $argsList+="--enable-network"
}

python @argsList
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "DASH2.05 SNAPSHOT REFRESH COMPLETE"
