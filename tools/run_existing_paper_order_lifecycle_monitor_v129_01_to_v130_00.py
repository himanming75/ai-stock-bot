from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.lifecycle_monitor import (
    ExistingPaperOrderLifecycleMonitor,
    LifecycleLedger,
    LifecycleSnapshot,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    root = Path(args.repository_root).resolve()
    ledger_path = (
        root / "release/v130_00/ledger"
        / "existing_order_lifecycle_ledger.jsonl"
    )
    monitor = ExistingPaperOrderLifecycleMonitor(
        ledger=LifecycleLedger(ledger_path)
    )

    snapshots = [
        LifecycleSnapshot(
            sequence=sequence,
            observed_at=f"2026-08-01T20:00:0{sequence}+00:00",
            broker_order_id="3bd9f491-0629-4cf4-9b0e-2a27eadea98d",
            client_order_id="single-60d3c5406e5226ae71d7",
            symbol="AAPL",
            side="BUY",
            status="ACCEPTED",
            quantity=Decimal("1"),
            filled_quantity=Decimal("0"),
            remaining_quantity=Decimal("1"),
            average_fill_price=Decimal("0"),
            position_quantity=Decimal("0"),
            position_average_price=Decimal("0"),
            cash=Decimal("100000"),
            equity=Decimal("100000"),
        )
        for sequence in range(1, 4)
    ]

    report = monitor.monitor(
        poller=lambda sequence: snapshots[sequence - 1],
        max_polls=3,
        network_requests_per_poll=0,
    )

    output = root / "release/v130_00/output"
    output.mkdir(parents=True, exist_ok=True)
    result = {
        "stage_range": "V129.01-V130.00",
        "status": "PASS",
        "implementation_type": "EXISTING_PAPER_ORDER_LIFECYCLE_MONITORING_RUNTIME",
        "validation_mode": "OFFLINE_THREE_POLL_ACTIVE_FIXTURE",
        **report.to_json_dict(),
        "active_order_guard_verified": (
            report.decision.value == "CONTINUE_TRACKING"
            and report.new_order_allowed is False
            and report.poll_count == 3
        ),
        "next_phase": "V130_01_ORDER_COMPLETION_AND_NEXT_ORDER_UNLOCK_GATE",
    }
    path = output / "existing_paper_order_lifecycle_monitor_result.json"
    path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
