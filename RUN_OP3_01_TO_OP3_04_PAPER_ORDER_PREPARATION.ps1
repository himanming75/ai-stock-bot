param(
    [string]$ApprovalPhrase = ""
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== OP3.01-OP3.04 CONTROLLED PAPER ORDER PREPARATION ==="
Write-Host "Preparation only. No network writes and no order submission."

$argsList = @(
    "tools/run_controlled_paper_order_preparation_op3_01_to_op3_04.py",
    "--repository-root",
    "."
)

if (-not [string]::IsNullOrWhiteSpace($ApprovalPhrase)) {
    $argsList += @("--approval-phrase", $ApprovalPhrase)
}

python @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OP3.01-OP3.04 COMPLETE"
