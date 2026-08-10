$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo

# Refresh the existing canonical feature snapshot locally first.
& "$Repo\.venv\Scripts\python.exe" `
 -m ai_engine_v2.signal_scoring_feature_snapshot_cli_v2_2_1 `
 --root $Repo
if($LASTEXITCODE -ne 0){
    Write-Host "V2.2.1 snapshot refresh returned non-zero; audit will use existing ledger."
}

& "$Repo\.venv\Scripts\python.exe" `
 -m broker_integration_v1.threshold_sensitivity_shadow_audit_cli_v2_1_31_4 `
 --root $Repo --mode audit
if($LASTEXITCODE -ne 0){throw "V2.1.31.4 AUDIT FAILED"}
