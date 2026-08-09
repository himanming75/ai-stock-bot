$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"

$Code=@'
from broker_integration_v1.etrade_current_market_wait_diagnostic_status_v2_1_7_1 import build_v2_1_7_1_wait_diagnostic_status
s=build_v2_1_7_1_wait_diagnostic_status()
print("STATUS:",s["status"])
print("CONNECTION STATUS VISIBLE:",s["websocket_connection_status_visible"])
print("AUTH STATUS VISIBLE:",s["auth_status_visible"])
print("SUBSCRIPTION STATUS VISIBLE:",s["subscription_status_visible"])
print("BAR PROGRESS VISIBLE:",s["per_symbol_bar_progress_visible"])
print("TIMEOUT DIAGNOSTICS:",s["timeout_diagnostics_visible"])
print("MARKET CLOSED CLAIM:",s["market_closed_claim_is_conservative"])
print("BROKER ORDER SUBMISSION:",s["broker_order_submission"])
print("PROD POST:",s["production_order_post_allowed"])
print("LIVE:",s["live_trading_enabled"])
assert s["status"]=="PASS_DEVELOPMENT_COMPLETE"
assert s["websocket_connection_status_visible"] is True
assert s["per_symbol_bar_progress_visible"] is True
assert s["market_closed_claim_is_conservative"] is True
assert s["broker_order_submission"] is False
assert s["production_order_post_allowed"] is False
assert s["live_trading_enabled"] is False
print("VERIFY: PASS")
'@

$Code | & $Python -
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
