$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_market_intelligence_data_fusion -v
python .\tools\verify_market_intelligence_data_fusion.py
