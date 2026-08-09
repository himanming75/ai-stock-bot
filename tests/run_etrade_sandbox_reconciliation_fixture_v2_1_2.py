from pathlib import Path
import tempfile
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.etrade_sandbox_order_reconciliation_v2_1_2 import reconcile_sandbox_place

cases=[
    (
        "MATCHED",
        {"OrdersResponse":{"Order":[{"orderId":1001}]}}
    ),
    (
        "SAMPLE_DATA_MISMATCH",
        {"OrdersResponse":{"Order":[{"orderId":9999}]}}
    ),
    (
        "NOT_OBSERVED",
        {"OrdersResponse":{"Order":[]}}
    ),
]
for expected,payload in cases:
    got=reconcile_sandbox_place({"order_id":"1001"},payload)
    print(expected,"=>",got["status"])
    if got["status"]!=expected:
        raise SystemExit(2)
print("V2.1.2 RECONCILIATION FIXTURE: PASS")
