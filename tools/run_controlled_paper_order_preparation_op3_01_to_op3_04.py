from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.controlled_paper_order_preparation import (
    ControlledPaperOrderPreparation,
    PAPER_BASE_URL,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--approval-phrase", default="")
    parser.add_argument("--base-url", default=PAPER_BASE_URL)
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()

    result = ControlledPaperOrderPreparation().run(
        dashboard_result_path=root/"release/dash1_01_to_dash1_04/actual/dashboard_snapshot.json",
        preparation_policy_path=root/"release/op3_01_to_op3_04/input/paper_order_preparation_policy.json",
        order_candidate_path=root/"release/op3_01_to_op3_04/input/paper_order_candidate.json",
        account_snapshot_path=root/"release/op3_01_to_op3_04/input/paper_account_snapshot.json",
        prepared_order_path=root/"release/op3_01_to_op3_04/actual/prepared_paper_order.json",
        risk_report_path=root/"release/op3_01_to_op3_04/actual/paper_order_preparation_risk_report.json",
        approval_gate_path=root/"release/op3_01_to_op3_04/actual/paper_order_manual_approval_gate.json",
        preparation_token_path=root/"release/op3_01_to_op3_04/actual/controlled_paper_order_preparation_token.json",
        result_path=root/"release/op3_01_to_op3_04/actual/controlled_paper_order_preparation_result.json",
        approval_phrase=args.approval_phrase,
        base_url=args.base_url,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print("RESULT_FILE=" + result["result_path"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
