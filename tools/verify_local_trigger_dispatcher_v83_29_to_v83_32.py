import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = (
    root / "release/v83_29_to_v83_32/actual/"
    "local_trigger_dispatcher_result.json"
)
if not path.exists():
    raise SystemExit("RESULT NOT FOUND: " + str(path))

result = json.loads(path.read_text(encoding="utf-8"))
checks = {
    "stage_range": result.get("stage_range") == "V83.29-V83.32",
    "status": result.get("status") == "PASS",
    "paper_only": result.get("paper_only") is True,
    "broker_write_disabled": result.get("broker_write_enabled") is False,
    "order_submission_disabled": result.get("order_submission_enabled") is False,
    "live_trading_disabled": result.get("live_trading_enabled") is False,
    "external_network_unused": result.get("actual_external_network_used") is False,
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("live_orders_submitted") == 0,
}
failed = [name for name, passed in checks.items() if not passed]
print(json.dumps({"checks": checks, "failed": failed}, indent=2))
raise SystemExit(1 if failed else 0)
