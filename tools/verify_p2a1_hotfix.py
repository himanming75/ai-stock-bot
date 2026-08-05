from __future__ import annotations
import inspect
import json

from broker_integration.execution_service import submit_paper_order


parameters = inspect.signature(submit_paper_order).parameters
checks = {
    "reference_price_removed": "reference_price" not in parameters,
    "latest_trade_price_present": "latest_trade_price" in parameters,
    "positions_present": "positions" in parameters,
}

result = {
    "verification_stage": "P2A1",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [name for name, passed in checks.items() if not passed],
    "actual_network_used": False,
    "actual_paper_orders_submitted": 0,
    "actual_live_orders_submitted": 0,
}
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
