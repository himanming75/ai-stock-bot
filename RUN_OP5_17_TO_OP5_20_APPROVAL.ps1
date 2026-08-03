param(
    [switch]$Approve,
    [string]$Approver = "",
    [string]$Reason = ""
)
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

Write-Host "=== OP5.17-OP5.20 PROMOTION APPROVAL LEDGER ==="
Write-Host "Explicit local approval record only. No broker or order operations."

$argsList=@(
    "tools/run_promotion_approval_op5_17_to_op5_20.py",
    "--repository-root",
    "."
)
if($Approve){$argsList+="--approve"}
if(-not [string]::IsNullOrWhiteSpace($Approver)){
    $argsList+=@("--approver",$Approver)
}
if(-not [string]::IsNullOrWhiteSpace($Reason)){
    $argsList+=@("--reason",$Reason)
}

python @argsList
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "OP5.17-OP5.20 COMPLETE"
