param(
[string]$ProjectPath="C:\stock-bot",
[string]$TargetCommit="2c80e6a9349959fb4bbfecdfc8e38b0f83a27f6e"
)
$ErrorActionPreference="Stop"
Set-Location -LiteralPath $ProjectPath
git status --short
git reset --hard $TargetCommit
if($LASTEXITCODE-ne 0){throw "ROLLBACK FAILED"}
Write-Host "RESTORED TO V119 COMMIT $TargetCommit"
