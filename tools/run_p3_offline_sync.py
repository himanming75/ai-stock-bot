from __future__ import annotations
from decimal import Decimal
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from broker_integration.p3_recovery import write_checkpoint
from broker_integration.p3_service import run_p3_sync
from broker_integration.paths import BrokerStatePaths


fixture = json.loads(
    (
        ROOT
        / "release/p3_order_fill_portfolio_sync/fixtures/"
          "p3_sync_fixture.json"
    ).read_text(encoding="utf-8-sig")
)

paths = BrokerStatePaths(ROOT)
actual = ROOT / "release/p3_order_fill_portfolio_sync/actual"

result = run_p3_sync(
    broker_account=fixture["broker_account"],
    broker_positions=fixture["broker_positions"],
    broker_orders=fixture["broker_orders"],
    local_portfolio=fixture["local_portfolio"],
    local_positions=fixture["local_positions"],
    fill_registry_path=actual / "fill_registry.json",
    fill_ledger_path=actual / "fill_ledger.jsonl",
    order_state_ledger_path=actual / "order_state_ledger.jsonl",
    drift_ledger_path=actual / "drift_ledger.jsonl",
    latest_result_path=actual / "p3_sync_result.json",
    position_tolerance=Decimal("0.000001"),
    account_tolerance=Decimal("1.00"),
)
write_checkpoint(paths.checkpoint, result)

summary = {
    "stage": result["stage"],
    "state": result["state"],
    "status": result["status"],
    "new_fill_count": result["new_fill_count"],
    "duplicate_fill_count": result["duplicate_fill_count"],
    "reconciliation_passed": result["reconciliation_passed"],
    "new_order_submission_allowed": result["new_order_submission_allowed"],
    "actual_paper_orders_submitted": 0,
    "actual_live_orders_submitted": 0,
}
print(json.dumps(summary, indent=2, sort_keys=True))
raise SystemExit(0 if result["status"] == "PASS" else 1)
