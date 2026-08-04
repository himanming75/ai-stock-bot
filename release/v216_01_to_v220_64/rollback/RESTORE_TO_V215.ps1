param([string]$ProjectPath="C:\stock-bot")
$ErrorActionPreference="Stop"
Set-Location $ProjectPath
Write-Host "=== RESTORE TO V215 / COMMIT 46c7008 ==="
Write-Host "This removes V216-V220 committed changes and returns the Git working tree to V215."
$status=git status --porcelain
if($status){
  Write-Host "ROLLBACK BLOCKED: Git working tree is not clean."
  git status --short
  exit 1
}
$answer=Read-Host "Type ROLLBACK to reset to 46c700805ea5e167cab01bf564ba162d435f9588"
if($answer -cne "ROLLBACK"){Write-Host "Cancelled.";exit 1}
git reset --hard 46c700805ea5e167cab01bf564ba162d435f9588
Write-Host "RESTORED TO V215."
Write-Host "Review locally before any force push. No remote branch was changed."
