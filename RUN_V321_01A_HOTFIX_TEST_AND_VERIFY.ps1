$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
Write-Host "=== V321.01A UNIT TEST ==="
& $Python -m unittest tools.test_v321_01_to_v330_64 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V321.01A VERIFY ==="
& $Python (Join-Path $Root "tools\verify_v321_01a_hotfix.py")
exit $LASTEXITCODE
