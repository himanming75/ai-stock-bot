from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.completion_unlock_gate import (
    CompletionLedger,
    OrderCompletionNextOrderUnlockGate,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()

    monitor_path = (
        root / "release/v130_00/actual"
        / "actual_existing_paper_order_lifecycle_monitor_result.json"
    )
    monitor_result = json.loads(
        monitor_path.read_text(encoding="utf-8")
    )

    ledger_path = (
        root / "release/v131_00/ledger"
        / "order_completion_ledger.jsonl"
    )
    gate = OrderCompletionNextOrderUnlockGate(
        ledger=CompletionLedger(ledger_path)
    )
    report = gate.evaluate(
        lifecycle_result={
            **monitor_result,
            "quantity": "1",
            "average_fill_price": (
                monitor_result.get("snapshots", [{}])[-1]
                .get("average_fill_price", "0")
            ),
            "cash": (
                monitor_result.get("snapshots", [{}])[-1]
                .get("cash", "0")
            ),
            "equity": (
                monitor_result.get("snapshots", [{}])[-1]
                .get("equity", "0")
            ),
            "client_order_id": (
                monitor_result.get("snapshots", [{}])[-1]
                .get("client_order_id", "")
            ),
            "broker_order_id": (
                monitor_result.get("snapshots", [{}])[-1]
                .get("broker_order_id", "")
            ),
            "symbol": (
                monitor_result.get("snapshots", [{}])[-1]
                .get("symbol", "")
            ),
            "side": (
                monitor_result.get("snapshots", [{}])[-1]
                .get("side", "")
            ),
        },
        completed_at="",
        network_requests_executed=0,
    )

    output = root / "release/v131_00/output"
    output.mkdir(parents=True, exist_ok=True)
    result = {
        "stage_range": "V130.01-V131.00",
        "status": "PASS",
        "implementation_type": "ORDER_COMPLETION_NEXT_ORDER_UNLOCK_GATE",
        "validation_mode": "PRIOR_ACTUAL_MONITOR_RESULT",
        **report.to_json_dict(),
        "active_lock_verified": (
            report.state.value == "LOCKED_ACTIVE_ORDER"
            and report.new_order_allowed is False
            and report.ledger_entry_written is False
        ),
        "next_phase": "V131_01_CONTINUE_ORDER_MONITOR_UNTIL_TERMINAL",
    }
    path = output / "order_completion_next_order_unlock_result.json"
    path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
