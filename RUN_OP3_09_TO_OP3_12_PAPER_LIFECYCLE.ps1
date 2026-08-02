param(
    [switch]$EnableNetwork
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== OP3.09-OP3.12 PAPER ORDER LIFECYCLE ==="
Write-Host "Read-only order, position, and account reconciliation. No writes."

$argsList = @(
    "tools/run_paper_order_lifecycle_op3_09_to_op3_12.py",
    "--repository-root",
    "."
)
if ($EnableNetwork) {
    $argsList += "--enable-network"
}

python @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OP3.09-OP3.12 COMPLETE"
