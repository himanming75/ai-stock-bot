$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

Write-Host "=== V1.8 SAFE WORKSPACE CLEANUP ==="

# Restore only the two tracked V1.7 files that were temporarily overwritten by failed V1.7.1 repair.
$trackedRestore=@(
  "tools/audit_holdout_zero_trade_v1_7.py",
  "tests/test_holdout_zero_trade_audit_v1_7.py"
)
foreach($p in $trackedRestore){
  $tracked=git ls-files --error-unmatch -- $p 2>$null
  if($LASTEXITCODE -eq 0){
    git restore --worktree -- $p
    Write-Host "RESTORED TRACKED: $p"
  }
}

# Remove only exact intermediate repair artifacts. Never wildcard project folders.
$removeExact=@(
  "RUN_V1_7_1.ps1","RUN_V1_7_2.ps1","RUN_V1_7_3.ps1",
  "VERIFY_V1_7_1.ps1","VERIFY_V1_7_2.ps1","VERIFY_V1_7_3.ps1",
  "tools/audit_holdout_zero_trade_v1_7_2.py",
  "tools/audit_holdout_zero_trade_v1_7_3.py",
  "tools/recover_alpaca_holdout_v1_7_3.py",
  "tests/test_holdout_zero_trade_audit_v1_7_2.py",
  "tests/test_v1_7_3_holdout_recovery.py",
  "release/v1_7_1_zero_trade_audit_repair",
  "release/v1_7_2_historical_source_recovery",
  "release/v1_7_3_alpaca_holdout_recovery"
)
foreach($p in $removeExact){
  if(Test-Path $p){
    # Never delete a tracked path.
    $tracked=git ls-files -- $p
    if($tracked){
      Write-Host "PRESERVE TRACKED: $p"
    } else {
      Remove-Item $p -Recurse -Force
      Write-Host "REMOVED INTERMEDIATE: $p"
    }
  }
}

Write-Host ""
Write-Host "CLEANUP STATUS:"
git status --short
