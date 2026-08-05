from decimal import Decimal
from pathlib import Path
import json
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from live_reconciliation.gates import evaluate_l4_gates
from live_reconciliation.service import reconcile_offline_fixture

expected_order = {
    "client_order_id": "l3-fixture-order",
    "symbol": "SPY",
    "side": "buy",
}
actual_order = {
    "id": "broker-fixture-order",
    "client_order_id": "l3-fixture-order",
    "symbol": "SPY",
    "side": "buy",
    "status": "filled",
    "filled_qty": "0.01",
    "filled_avg_price": "500",
}
positions = [{
    "symbol": "SPY",
    "qty": "0.01",
    "avg_entry_price": "500",
    "market_value": "5",
}]

result = reconcile_offline_fixture(
    root=ROOT,
    expected_order=expected_order,
    actual_order=actual_order,
    expected_positions=positions,
    actual_positions=positions,
    expected_cash=Decimal("995"),
    actual_cash=Decimal("995"),
    expected_buying_power=Decimal("995"),
    actual_buying_power=Decimal("995"),
    fill_key=f"fixture-{uuid.uuid4().hex}",
)
result["gates"] = evaluate_l4_gates(ROOT)
result["actual_live_reconciliation_allowed"] = False

path = (
    ROOT / "release/l4_live_reconciliation_preparation/actual/"
           "l4_offline_qualification.json"
)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(
    json.dumps(result, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(result, indent=2, sort_keys=True))
