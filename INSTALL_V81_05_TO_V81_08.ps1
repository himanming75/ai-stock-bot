param([string]$RepositoryRoot="C:\stock-bot")
$ErrorActionPreference="Stop"
$BundleRoot=Split-Path -Parent $MyInvocation.MyCommand.Path
$files=@("shadow_trading\execution_engine_v81_05_08.py","dashboard\shadow_execution_integration.py","tools\run_shadow_execution_v81_05_to_v81_08.py","tools\test_shadow_execution_v81_05_to_v81_08.py","tools\install_check_v81_05_to_v81_08.py","tools\verify_shadow_execution_v81_05_to_v81_08.py","RUN_V81_05_TO_V81_08_SHADOW_EXECUTION.ps1","RUN_V81_05_TO_V81_08_TEST_AND_VERIFY.ps1","V81_05_TO_V81_08_MANIFEST.json","GIT_COMMIT_V81_05_TO_V81_08.txt")
foreach($rel in $files){$src=Join-Path $BundleRoot $rel;$dst=Join-Path $RepositoryRoot $rel;New-Item -ItemType Directory -Path (Split-Path -Parent $dst) -Force|Out-Null;Copy-Item -LiteralPath $src -Destination $dst -Force}
$src=Join-Path $BundleRoot "release\v81_05_to_v81_08";$dst=Join-Path $RepositoryRoot "release\v81_05_to_v81_08";New-Item -ItemType Directory -Path $dst -Force|Out-Null;Copy-Item -Path (Join-Path $src "*") -Destination $dst -Recurse -Force
Write-Host "V81_05_TO_V81_08_INSTALL=PASS"
