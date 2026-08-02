param([switch]$EnableNetwork)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
Write-Host "=== OP1.01-OP1.04 PAPER OPERATIONS PILOT ==="
Write-Host "Read-only Paper preflight. No order submission and no Live trading."
$argsList = @("tools/run_paper_operations_pilot_op1_01_to_op1_04.py", "--repository-root", ".")
if ($EnableNetwork) { $argsList += "--enable-network" }
python @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "OP1.01-OP1.04 COMPLETE"
