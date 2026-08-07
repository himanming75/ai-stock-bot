[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
$OutputEncoding=[System.Text.Encoding]::UTF8
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}
& $Python -c "import json; from pathlib import Path; import validation_analytics_v3 as v; print(json.dumps(v.lifecycle_replay_diagnostics(Path(r'C:\stock-bot')),indent=2,default=str))"
exit $LASTEXITCODE
