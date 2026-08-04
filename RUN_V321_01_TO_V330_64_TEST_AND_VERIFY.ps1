$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
Write-Host "=== INSTALL CHECK ==="
& $Python (Join-Path $PSScriptRoot "tools\install_check_v321_01_to_v330_64.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== UNIT TEST ==="
& $Python -m unittest tools.test_v321_01_to_v330_64 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== VERIFY ==="
& $Python (Join-Path $PSScriptRoot "tools\verify_v321_01_to_v330_64.py")
exit $LASTEXITCODE
