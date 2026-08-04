param([string]$ProjectPath="C:\stock-bot")
$ErrorActionPreference="Stop"
Set-Location $ProjectPath
git checkout 4d91678d8c59bd3fbca4c06a1a41eef7c4c4949f -- .
Write-Host "RESTORED WORKING TREE TO V139 BASE CONTENT"
Write-Host "Review git status before committing."
