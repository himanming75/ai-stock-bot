$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$env:PYTHONPATH = $Root
& $Python (Join-Path $Root "tools\run_paper_completion_certificate.py")
exit $LASTEXITCODE
