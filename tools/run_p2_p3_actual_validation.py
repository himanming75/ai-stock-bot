from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from broker_integration.actual_validation import (
    build_clients,
    poll_order,
    write_p2_validation,
    write_p3_validation,
)

parser = argparse.ArgumentParser()
parser.add_argument("--client-order-id", required=True)
parser.add_argument("--timeout-seconds", type=int, default=180)
parser.add_argument("--poll-seconds", type=int, default=5)
args = parser.parse_args()

config, read_adapter, execution_http = build_clients()
order = poll_order(
    execution_http,
    args.client_order_id,
    args.timeout_seconds,
    args.poll_seconds,
)
p2 = write_p2_validation(ROOT, order)
p3 = write_p3_validation(
    ROOT,
    order=order,
    read_adapter=read_adapter,
)

summary = {
    "p2_actual_validated": p2["validated"],
    "p3_actual_validated": p3["validated"],
    "client_order_id": args.client_order_id,
    "broker_order_id": order.get("id", ""),
    "order_status": order.get("status", ""),
    "filled_qty": order.get("filled_qty", "0"),
    "filled_avg_price": order.get("filled_avg_price"),
    "actual_live_orders_submitted": 0,
}
print(json.dumps(summary, indent=2, sort_keys=True))
raise SystemExit(
    0 if p2["validated"] and p3["validated"] else 1
)
