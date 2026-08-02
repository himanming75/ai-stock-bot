from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.single_controlled_paper_order_execution import (
    PAPER_BASE_URL,
    SingleControlledPaperOrderExecution,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument(
        "--enable-network",
        action="store_true",
    )
    parser.add_argument(
        "--enable-submission",
        action="store_true",
    )
    parser.add_argument("--approval-phrase", default="")
    parser.add_argument("--base-url", default=PAPER_BASE_URL)
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()

    result = SingleControlledPaperOrderExecution().run(
        preparation_result_path=root/"release/op3_01_to_op3_04/actual/controlled_paper_order_preparation_result.json",
        prepared_order_path=root/"release/op3_01_to_op3_04/actual/prepared_paper_order.json",
        execution_policy_path=root/"release/op3_05_to_op3_08/input/single_paper_order_execution_policy.json",
        submission_receipt_path=root/"release/op3_05_to_op3_08/actual/single_paper_order_submission_receipt.json",
        execution_ledger_path=root/"release/op3_05_to_op3_08/actual/single_paper_order_execution_ledger.jsonl",
        execution_token_path=root/"release/op3_05_to_op3_08/actual/single_paper_order_execution_token.json",
        result_path=root/"release/op3_05_to_op3_08/actual/single_controlled_paper_order_execution_result.json",
        enable_network=args.enable_network,
        enable_submission=args.enable_submission,
        approval_phrase=args.approval_phrase,
        base_url=args.base_url,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print("RESULT_FILE=" + result["result_path"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
