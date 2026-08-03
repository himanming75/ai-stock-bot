
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = (
    ROOT / "release/v82_17_to_v82_20/actual/"
    "shadow_trade_authorization_result.json"
)
if not path.exists():
    raise SystemExit("VERIFY=FAIL result missing")

result = json.loads(path.read_text(encoding="utf-8"))
checks = {
    "status": result.get("status") == "PASS",
    "shadow": result.get("shadow_only") is True,
    "readonly": result.get("read_only") is True,
    "broker": result.get("broker_write_enabled") is False,
    "orders": result.get("order_submission_enabled") is False,
    "network": result.get("network_requests_executed") == 0,
    "writes": result.get("write_requests_executed") == 0,
    "ledger": result.get("authorization_ledger_written") is True,
    "snapshot": result.get("authorization_snapshot_written") is True,
    "dashboard": result.get("dashboard_state_written") is True,
    "state": result.get("state") in {
        "SHADOW_TRADE_AUTHORIZED",
        "SHADOW_TRADE_NO_ACTION",
        "SHADOW_TRADE_REJECTED",
    },
}
failed = [name for name, passed in checks.items() if not passed]
if failed:
    raise SystemExit("VERIFY=FAIL " + ",".join(failed))
print("VERIFY=PASS")
