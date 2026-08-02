from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.shadow_decision_bootstrap import (
    ShadowDecisionBootstrap,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()

    result = ShadowDecisionBootstrap().run(
        scheduled_result_path=root/"release/op1_17_to_op1_20/actual/windows_scheduled_collection_result.json",
        shadow_policy_path=root/"release/op2_01_to_op2_04/input/shadow_policy.json",
        signal_snapshot_path=root/"release/op2_01_to_op2_04/input/shadow_signal_snapshot.json",
        portfolio_snapshot_path=root/"release/op2_01_to_op2_04/input/shadow_portfolio_snapshot.json",
        shadow_decision_path=root/"release/op2_01_to_op2_04/actual/shadow_decision.json",
        risk_report_path=root/"release/op2_01_to_op2_04/actual/shadow_risk_report.json",
        shadow_ledger_path=root/"release/op2_01_to_op2_04/actual/shadow_decision_ledger.jsonl",
        shadow_token_path=root/"release/op2_01_to_op2_04/actual/shadow_decision_token.json",
        result_path=root/"release/op2_01_to_op2_04/actual/shadow_decision_bootstrap_result.json",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print("RESULT_FILE=" + result["result_path"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
