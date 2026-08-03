import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = (
    ROOT / "release/v81_09_to_v81_12/actual/"
    "shadow_portfolio_result.json"
)
if not path.exists():
    raise SystemExit("VERIFY=FAIL result missing")

result = json.loads(path.read_text(encoding="utf-8"))
checks = {
    "status": result.get("status") == "PASS",
    "shadow_only": result.get("shadow_only") is True,
    "read_only": result.get("read_only") is True,
    "broker_write": result.get("broker_write_enabled") is False,
    "order_submission": (
        result.get("order_submission_enabled") is False
    ),
    "network": result.get("network_requests_executed") == 0,
    "writes": result.get("write_requests_executed") == 0,
    "paper_orders": result.get("actual_paper_orders_submitted") == 0,
    "live_orders": result.get("live_orders_submitted") == 0,
    "portfolio": result.get("portfolio_state_written") is True,
    "equity": result.get("equity_history_written") is True,
    "daily": result.get("daily_report_written") is True,
    "dashboard": result.get("dashboard_state_written") is True,
    "recovery": result.get("recovery_snapshot_written") is True,
    "state": result.get("state") in {
        "WAIT_SHADOW_EXECUTION",
        "SHADOW_PORTFOLIO_UPDATED",
        "SHADOW_PORTFOLIO_NO_CHANGE",
        "SHADOW_PORTFOLIO_RISK_LIMIT",
    },
}
failed = [name for name, passed in checks.items() if not passed]
if failed:
    raise SystemExit("VERIFY=FAIL " + ",".join(failed))
print("VERIFY=PASS")
