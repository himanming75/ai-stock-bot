$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python .\tools\run_etrade_sandbox_token_action.py revoke
