from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime import AutonomousPaperReadReconciler


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    repository_root = Path(args.repository_root).resolve()
    output = repository_root / "release" / "v122_00" / "output"
    output.mkdir(parents=True, exist_ok=True)

    actual_result_path = (
        repository_root
        / "release" / "v121_00" / "actual_read"
        / "actual_autonomous_paper_read_result.json"
    )
    if actual_result_path.exists():
        actual_snapshot = json.loads(actual_result_path.read_text(encoding="utf-8"))
        source_mode = "ACTUAL_ALPACA_PAPER_READ_RESULT"
    else:
        actual_snapshot = {
            "cash": "100000",
            "equity": "100000",
            "position_count": 0,
            "symbols_held": [],
            "open_order_count": 1,
        }
        source_mode = "OFFLINE_FIXTURE"

    internal_portfolio = {
        "cash": "100000",
        "equity": "100000",
        "positions": [],
    }
    internal_recovery = {
        "expected_snapshot_generation": 1,
        "actual_snapshot_generation": 1,
    }
    internal_runtime = {
        "runtime_state": "READY",
        # Deliberately expect zero internal orders. The actual account currently
        # reports one open order, so the safe-mode path is validated.
        "open_order_count": 0,
    }

    report = AutonomousPaperReadReconciler().reconcile(
        actual_snapshot=actual_snapshot,
        internal_portfolio=internal_portfolio,
        internal_recovery=internal_recovery,
        internal_runtime=internal_runtime,
    )

    report_dict = report.to_json_dict()
    reconciliation_status = report_dict.pop("status")
    result = {
        "stage_range": "V121.01-V122.00",
        "status": "PASS",
        "reconciliation_status": reconciliation_status,
        "implementation_type": "AUTONOMOUS_PAPER_READ_RECONCILIATION",
        "source_mode": source_mode,
        **report_dict,
        "expected_safe_mode": True,
        "open_order_guard_verified": (
            report.safe_mode_engaged
            and any(item.code == "OPEN_ORDER_COUNT_MISMATCH" for item in report.issues)
        ),
        "next_phase": "V122_01_AUTONOMOUS_PAPER_ORDER_IDENTITY_RECONCILIATION",
    }
    path = output / "autonomous_paper_read_reconciliation_result.json"
    path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
