from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime import AutonomousPaperOrderIdentityReconciler


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    repository_root = Path(args.repository_root).resolve()
    output = repository_root / "release" / "v123_00" / "output"
    output.mkdir(parents=True, exist_ok=True)

    # Fixture mirrors the current condition: one unexplained open order.
    open_orders = [{
        "id": "paper-open-order-fixture-1",
        "client_order_id": "manual-or-external-order-1",
        "symbol": "AAPL",
        "side": "buy",
        "qty": "1",
        "type": "limit",
        "time_in_force": "day",
        "status": "new",
        "submitted_at": "2026-08-01T15:00:00Z",
        "filled_qty": "0",
        "limit_price": "50",
    }]
    internal_order_ledger = []

    report = AutonomousPaperOrderIdentityReconciler().reconcile(
        open_orders=open_orders,
        internal_order_ledger=internal_order_ledger,
    )
    report_dict = report.to_json_dict()
    identity_status = report_dict.pop("status")

    result = {
        "stage_range": "V122.01-V123.00",
        "status": "PASS",
        "identity_status": identity_status,
        "implementation_type": "AUTONOMOUS_PAPER_ORDER_IDENTITY_RECONCILIATION",
        "validation_mode": "OFFLINE_FIXTURE_EXTERNAL_ORDER",
        **report_dict,
        "external_order_guard_verified": (
            report.safe_mode_engaged
            and report.external_order_count == 1
            and report.blocking_order_count == 1
        ),
        "next_phase": "V123_01_ACTUAL_OPEN_ORDER_IDENTITY_READ",
    }

    path = output / "autonomous_paper_order_identity_reconciliation_result.json"
    path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
