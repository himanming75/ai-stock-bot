$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"

$Code=@'
from broker_integration_v1.historical_bootstrap_diagnostic_status_v2_1_8_1 import build_v2_1_8_1_status
s=build_v2_1_8_1_status()
print("STATUS:",s["status"])
print("HTTP STATUS VISIBLE:",s["http_status_visible"])
print("SAFE HEADERS VISIBLE:",s["safe_headers_visible"])
print("SYMBOL RAW COUNTS:",s["symbol_raw_counts_visible"])
print("FIRST/LAST TS:",s["first_last_timestamp_visible"])
print("PAGINATION:",s["pagination_supported"])
print("BROKER ORDER SUBMISSION:",s["broker_order_submission"])
print("PROD POST:",s["production_order_post_allowed"])
print("LIVE:",s["live_trading_enabled"])
assert s["status"]=="PASS_DEVELOPMENT_COMPLETE"
assert s["pagination_supported"] is True
assert s["broker_order_submission"] is False
assert s["production_order_post_allowed"] is False
assert s["live_trading_enabled"] is False
print("VERIFY: PASS")
'@

$Code | & $Python -
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
