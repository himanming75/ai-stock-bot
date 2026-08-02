from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_pilot.promotion_gate import PaperPilotPromotionGate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()

    result = PaperPilotPromotionGate().run(
        policy_path=root/"release/op5_13_to_op5_16/input/promotion_policy.json",
        validation_summary_path=root/"release/op5_01_to_op5_04/actual/multi_day_validation_summary.json",
        validation_gate_path=root/"release/op5_01_to_op5_04/actual/multi_day_validation_gate.json",
        analytics_result_path=root/"release/op5_05_to_op5_08/actual/validation_analytics_result.json",
        certificate_result_path=root/"release/op5_09_to_op5_12/actual/validation_certificate_result.json",
        risk_result_path=root/"release/op4_13_to_op4_16/actual/paper_risk_monitor_result.json",
        promotion_manifest_path=root/"release/op5_13_to_op5_16/actual/promotion_manifest.json",
        dashboard_state_path=root/"release/op5_13_to_op5_16/actual/promotion_dashboard_state.json",
        result_path=root/"release/op5_13_to_op5_16/actual/promotion_gate_result.json",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print("RESULT_FILE=" + result["result_path"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
