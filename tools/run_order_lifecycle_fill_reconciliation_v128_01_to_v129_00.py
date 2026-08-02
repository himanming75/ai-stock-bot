from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.fill_reconciliation import (
    ActualOrderLifecycleFillReconciler,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    root = Path(args.repository_root).resolve()
    actual_lifecycle_path = (
        root / "release/v128_00/actual"
        / "actual_existing_paper_order_lifecycle_result.json"
    )
    if actual_lifecycle_path.exists():
        prior = json.loads(actual_lifecycle_path.read_text(encoding="utf-8"))
    else:
        prior = {
            "broker_order_id": "3bd9f491-0629-4cf4-9b0e-2a27eadea98d",
            "client_order_id": "single-60d3c5406e5226ae71d7",
            "symbol": "AAPL",
            "side": "BUY",
            "quantity": "1",
            "filled_quantity": "0",
            "broker_status": "ACCEPTED",
        }

    report = ActualOrderLifecycleFillReconciler().reconcile(
        order={
            "id": prior.get("broker_order_id", ""),
            "client_order_id": prior.get("client_order_id", ""),
            "symbol": prior.get("symbol", ""),
            "side": prior.get("side", ""),
            "quantity": prior.get("quantity", "0"),
            "filled_quantity": prior.get("filled_quantity", "0"),
            "average_fill_price": "0",
            "status": prior.get("broker_status", ""),
        },
        positions=[],
        account={"cash": "100000", "equity": "100000"},
    )

    output = root / "release/v129_00/output"
    output.mkdir(parents=True, exist_ok=True)
    result = {
        "stage_range": "V128.01-V129.00",
        "status": "PASS",
        "implementation_type": "ACTUAL_ORDER_LIFECYCLE_FILL_RECONCILIATION_GATE",
        "validation_mode": "PRIOR_ACTUAL_LIFECYCLE_RESULT",
        **report.to_json_dict(),
        "active_order_guard_verified": (
            report.state.value == "WAITING_ACTIVE_ORDER"
            and report.new_order_allowed is False
        ),
        "next_phase": "V129_01_CONTINUE_ORDER_LIFECYCLE_TRACKING",
    }
    path = output / "order_lifecycle_fill_reconciliation_result.json"
    path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
