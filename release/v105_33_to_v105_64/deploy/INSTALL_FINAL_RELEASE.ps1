param(
    [string]$ProjectPath = "C:\stock-bot"
)
$ErrorActionPreference = "Stop"
Write-Host "V105 FINAL RELEASE INSTALL WRAPPER"
powershell -ExecutionPolicy Bypass `
    -File "$PSScriptRoot\..\..\..\INSTALL_AND_SAVE_V105_33_TO_V105_64_ONE_CLICK.ps1" `
    -ProjectPath $ProjectPath `
    -SkipPush
