from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.submitted_order_acceptance_verification import (
    SubmittedOrderAcceptanceVerification,
)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repository-root", default=".")
    p.add_argument("--launch-result-path", default="release/v139_07/actual/autonomous_paper_order_launch_result.json")
    p.add_argument("--preparation-token-path", default="release/v139_07/actual/order_submission_preparation_token.json")
    p.add_argument("--preview-path", default="release/v139_07/actual/order_launch_preview.json")
    p.add_argument("--submission-snapshot-path", default="release/v139_08/input/submitted_order_result_snapshot.json")
    p.add_argument("--acceptance-token-path", default="release/v139_08/actual/submitted_order_acceptance_token.json")
    p.add_argument("--result-path", default="release/v139_08/actual/submitted_order_acceptance_verification_result.json")
    a = p.parse_args()
    root = Path(a.repository_root).resolve()
    report = SubmittedOrderAcceptanceVerification().run(
        launch_result_path=root / a.launch_result_path,
        preparation_token_path=root / a.preparation_token_path,
        preview_path=root / a.preview_path,
        submission_snapshot_path=root / a.submission_snapshot_path,
        acceptance_token_path=root / a.acceptance_token_path,
        result_path=root / a.result_path,
    )
    print(json.dumps(report.to_json_dict(), indent=2, sort_keys=True))
    print(f"RESULT_FILE={(root / a.result_path).resolve()}")
    return 0 if report.status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
