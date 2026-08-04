$ErrorActionPreference="Stop"
$R=Split-Path -Parent $MyInvocation.MyCommand.Path;$P=Join-Path $R ".venv\Scripts\python.exe";if(-not(Test-Path $P)){$P="python"}
$C=Read-Host "Type ENABLE_CONTROLLED_PAPER_AUTO_EXECUTION";if($C-ne"ENABLE_CONTROLLED_PAPER_AUTO_EXECUTION"){throw "Confirmation phrase did not match."}
&$P (Join-Path $R "tools\run_v361_01_to_v370_64.py") --allow-paper-network --enable-phrase "ENABLE_CONTROLLED_PAPER_AUTO_EXECUTION";exit $LASTEXITCODE
