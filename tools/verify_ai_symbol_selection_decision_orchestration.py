from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "release/ai_symbol_selection_decision_orchestration/actual/ai_decision_snapshot.json"


def main() -> int:
    test = subprocess.run(
        [sys.executable, "-m", "unittest",
         "tools.test_ai_symbol_selection_decision_orchestration", "-v"],
        cwd=ROOT, check=False,
    )
    if test.returncode:
        print("VERIFY: FAIL (unit tests)")
        return test.returncode

    run = subprocess.run(
        [sys.executable, "tools/run_ai_symbol_selection_decision_orchestration.py"],
        cwd=ROOT, check=False,
    )
    if run.returncode:
        print("VERIFY: FAIL (runner)")
        return run.returncode

    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    invariants = {
        "actual_external_network_used": False,
        "actual_broker_write_performed": False,
        "actual_order_submission_performed": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }
    failed = [k for k, v in invariants.items() if payload.get(k) != v]
    if payload.get("status") != "PASS" or failed:
        print(f"VERIFY: FAIL {failed}")
        return 1

    print("VERIFY: PASS")
    print("NETWORK: OFF")
    print("BROKER WRITE: OFF")
    print("PAPER ORDERS: 0")
    print("LIVE ORDERS: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
