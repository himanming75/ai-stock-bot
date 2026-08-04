$ErrorActionPreference = "Stop"
$ProjectRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $PSScriptRoot "..\..\..")
)
Set-Location $ProjectRoot
powershell -ExecutionPolicy Bypass `
    -File .\RUN_V105_33_TO_V105_64_TEST_AND_VERIFY.ps1
