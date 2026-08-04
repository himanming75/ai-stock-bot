$ErrorActionPreference="Stop"
$R=Split-Path -Parent $MyInvocation.MyCommand.Path;$P=Join-Path $R ".venv\Scripts\python.exe";if(-not(Test-Path $P)){$P="python"}
Write-Host "=== V361.01-V370.64 UNIT TEST ===";&$P -m unittest tools.test_v361_01_to_v370_64 -v;if($LASTEXITCODE-ne0){exit $LASTEXITCODE}
Write-Host "=== V361.01-V370.64 SAFE DRY RUN ===";&$P (Join-Path $R "tools\run_v361_01_to_v370_64.py");if($LASTEXITCODE-ne0){exit $LASTEXITCODE}
Write-Host "=== V361.01-V370.64 VERIFY ===";&$P (Join-Path $R "tools\verify_v361_01_to_v370_64.py");exit $LASTEXITCODE
