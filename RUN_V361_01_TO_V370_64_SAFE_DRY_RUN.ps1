$ErrorActionPreference="Stop"
$R=Split-Path -Parent $MyInvocation.MyCommand.Path;$P=Join-Path $R ".venv\Scripts\python.exe";if(-not(Test-Path $P)){$P="python"}
&$P (Join-Path $R "tools\run_v361_01_to_v370_64.py");exit $LASTEXITCODE
