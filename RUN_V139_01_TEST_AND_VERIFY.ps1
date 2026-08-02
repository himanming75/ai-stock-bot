$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python tools/install_check_v139_01.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python -m unittest tools.test_actual_terminal_monitor_continuation_v139_01 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
powershell -ExecutionPolicy Bypass -File .\RUN_V139_01_ACTUAL_TERMINAL_MONITOR_CONTINUATION.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_actual_terminal_monitor_continuation_v139_01.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V139.01 TEST AND VERIFY PASS"
