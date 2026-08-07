[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
$OutputEncoding=[System.Text.Encoding]::UTF8
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}
& $Python .\tools\build_real_market_multitimeframe_shadow.py --root $PSScriptRoot --mode rolling
exit $LASTEXITCODE
