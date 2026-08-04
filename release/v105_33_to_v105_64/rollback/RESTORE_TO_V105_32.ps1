param(
    [string]$ProjectPath = "C:\stock-bot",
    [string]$TargetCommit = "5724090"
)
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $ProjectPath

Write-Host "This rollback preserves release actual ledgers where possible."
git status --short
git reset --hard $TargetCommit
if($LASTEXITCODE -ne 0){
    throw "ROLLBACK FAILED"
}
Write-Host "RESTORED TO V105.32 COMMIT $TargetCommit"
