from pathlib import Path
import argparse, json, sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.paper_order_lifecycle_reconciliation import (
    PAPER_BASE_URL,
    PaperOrderLifecycleReconciliation,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--enable-network", action="store_true")
    parser.add_argument("--base-url", default=PAPER_BASE_URL)
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()

    result = PaperOrderLifecycleReconciliation().run(
        execution_result_path=root/"release/op3_05_to_op3_08/actual/single_controlled_paper_order_execution_result.json",
        submission_receipt_path=root/"release/op3_05_to_op3_08/actual/single_paper_order_submission_receipt.json",
        lifecycle_policy_path=root/"release/op3_09_to_op3_12/input/paper_order_lifecycle_policy.json",
        local_order_snapshot_path=root/"release/op3_09_to_op3_12/input/local_paper_order_snapshot.json",
        local_positions_snapshot_path=root/"release/op3_09_to_op3_12/input/local_paper_positions_snapshot.json",
        local_account_snapshot_path=root/"release/op3_09_to_op3_12/input/local_paper_account_snapshot.json",
        order_status_path=root/"release/op3_09_to_op3_12/actual/paper_order_status.json",
        fill_report_path=root/"release/op3_09_to_op3_12/actual/paper_order_fill_report.json",
        reconciliation_report_path=root/"release/op3_09_to_op3_12/actual/paper_position_reconciliation_report.json",
        recovery_token_path=root/"release/op3_09_to_op3_12/actual/paper_order_recovery_token.json",
        audit_ledger_path=root/"release/op3_09_to_op3_12/actual/paper_order_lifecycle_audit_ledger.jsonl",
        result_path=root/"release/op3_09_to_op3_12/actual/paper_order_lifecycle_result.json",
        enable_network=args.enable_network,
        base_url=args.base_url,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print("RESULT_FILE=" + result["result_path"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
