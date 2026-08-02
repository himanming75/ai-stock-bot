param(
    [switch]$EnableNetwork,
    [switch]$EnableSubmission,
    [string]$ApprovalPhrase = ""
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V140.10-V140.12 ALPACA PAPER INTEGRATION ==="
Write-Host "Default mode is local snapshot only. Live endpoint is always blocked."

$argsList = @(
    "tools/run_alpaca_paper_integration_bundle_v140_10_to_v140_12.py",
    "--repository-root", "."
)
if ($EnableNetwork) { $argsList += "--enable-network" }
if ($EnableSubmission) { $argsList += "--enable-submission" }
if (-not [string]::IsNullOrWhiteSpace($ApprovalPhrase)) {
    $argsList += @("--approval-phrase", $ApprovalPhrase)
}

python @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V140.10-V140.12 COMPLETE"
