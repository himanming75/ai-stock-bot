from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_pilot.validation_certificate import (
    ValidationCertificateFoundation,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--issue-certificate", action="store_true")
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()

    result = ValidationCertificateFoundation().run(
        policy_path=root/"release/op5_09_to_op5_12/input/validation_certificate_policy.json",
        validation_summary_path=root/"release/op5_01_to_op5_04/actual/multi_day_validation_summary.json",
        validation_gate_path=root/"release/op5_01_to_op5_04/actual/multi_day_validation_gate.json",
        analytics_result_path=root/"release/op5_05_to_op5_08/actual/validation_analytics_result.json",
        certificate_path=root/"release/op5_09_to_op5_12/actual/validation_certificate.json",
        seal_path=root/"release/op5_09_to_op5_12/actual/validation_certificate.sha256",
        manifest_path=root/"release/op5_09_to_op5_12/actual/validation_certificate_manifest.json",
        verify_path=root/"release/op5_09_to_op5_12/actual/validation_certificate_verify.json",
        dashboard_state_path=root/"release/op5_09_to_op5_12/actual/validation_certificate_dashboard_state.json",
        result_path=root/"release/op5_09_to_op5_12/actual/validation_certificate_result.json",
        issue_certificate=args.issue_certificate,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print("RESULT_FILE=" + result["result_path"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
