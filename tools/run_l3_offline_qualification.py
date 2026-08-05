from decimal import Decimal
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from live_execution.client_order_id import build_live_client_order_id
from live_execution.dry_run import LiveDryRunTransport
from live_execution.gates import evaluate_l3_gates
from live_execution.models import LiveMicroOrder
from live_execution.service import prepare_live_micro_order

client_order_id = build_live_client_order_id(
    "SPY", "buy", "l3-offline-qualification"
)
order = LiveMicroOrder(
    symbol="SPY",
    side="buy",
    order_type="market",
    time_in_force="day",
    notional=Decimal("1"),
    client_order_id=client_order_id,
)
result = prepare_live_micro_order(
    root=ROOT,
    order=order,
    estimated_notional=Decimal("1"),
    maximum_order_notional=Decimal("10"),
    daily_order_count=0,
    maximum_daily_orders=1,
    daily_realized_loss=Decimal("0"),
    maximum_daily_loss=Decimal("10"),
    allowed_symbols=("SPY",),
    transport=LiveDryRunTransport(),
)
result["gates"] = evaluate_l3_gates(ROOT)
result["actual_live_execution_allowed"] = False

path = (
    ROOT / "release/l3_live_micro_execution_preparation/actual/"
           "l3_offline_qualification.json"
)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(
    json.dumps(result, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(result, indent=2, sort_keys=True))
