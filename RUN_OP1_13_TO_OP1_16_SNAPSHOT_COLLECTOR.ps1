param([switch]$EnableNetwork)
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
Write-Host "=== OP1.13-OP1.16 AUTOMATIC SNAPSHOT COLLECTOR ==="
Write-Host "Paper GET-only collection and snapshot rotation. No orders."
$argsList=@("tools/run_automatic_snapshot_collector_op1_13_to_op1_16.py","--repository-root",".")
if($EnableNetwork){$argsList+="--enable-network"}
python @argsList
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "OP1.13-OP1.16 COMPLETE"
