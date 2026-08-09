$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"

$Code=@'
from broker_integration_v1.historical_bootstrap_symbol_scope_status_v2_1_8_2 import build_v2_1_8_2_status
s=build_v2_1_8_2_status()
print("STATUS:",s["status"])
print("SYMBOL-SCOPED REST:",s["symbol_scoped_rest_requests"])
print("MULTI-SYMBOL PAGINATION DEPENDENCY REMOVED:",s["multi_symbol_pagination_dependency_removed"])
print("PER-SYMBOL PAGINATION BOUNDED:",s["per_symbol_pagination_bounded"])
print("BROKER ORDER SUBMISSION:",s["broker_order_submission"])
print("PROD POST:",s["production_order_post_allowed"])
print("LIVE:",s["live_trading_enabled"])
assert s["status"]=="PASS_DEVELOPMENT_COMPLETE"
assert s["symbol_scoped_rest_requests"] is True
assert s["multi_symbol_pagination_dependency_removed"] is True
assert s["broker_order_submission"] is False
assert s["production_order_post_allowed"] is False
assert s["live_trading_enabled"] is False
print("VERIFY: PASS")
'@
$Code | & $Python -
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
