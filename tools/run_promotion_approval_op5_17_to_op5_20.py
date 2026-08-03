from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_pilot.promotion_approval import PromotionApprovalLedger


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--approve", action="store_true")
    parser.add_argument("--approver", default="")
    parser.add_argument("--reason", default="")
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()

    result = PromotionApprovalLedger().run(
        policy_path=root/"release/op5_17_to_op5_20/input/promotion_approval_policy.json",
        promotion_gate_result_path=root/"release/op5_13_to_op5_16/actual/promotion_gate_result.json",
        certificate_result_path=root/"release/op5_09_to_op5_12/actual/validation_certificate_result.json",
        approval_ledger_path=root/"release/op5_17_to_op5_20/actual/promotion_approval_ledger.jsonl",
        approval_record_path=root/"release/op5_17_to_op5_20/actual/latest_promotion_approval.json",
        approval_manifest_path=root/"release/op5_17_to_op5_20/actual/promotion_approval_manifest.json",
        certification_gate_path=root/"release/op5_17_to_op5_20/actual/paper_pilot_certification_gate.json",
        dashboard_state_path=root/"release/op5_17_to_op5_20/actual/promotion_approval_dashboard_state.json",
        result_path=root/"release/op5_17_to_op5_20/actual/promotion_approval_result.json",
        approve=args.approve,
        approver=args.approver,
        approval_reason=args.reason,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print("RESULT_FILE=" + result["result_path"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
