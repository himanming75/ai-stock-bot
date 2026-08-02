from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.autonomous_paper_order_launch import AutonomousPaperOrderLaunch


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repository-root", default=".")
    p.add_argument("--eligibility-result-path", default="release/v139_06/actual/next_order_eligibility_result.json")
    p.add_argument("--eligibility-token-path", default="release/v139_06/actual/next_order_eligibility_token.json")
    p.add_argument("--order-candidate-path", default="release/v139_07/input/order_candidate.json")
    p.add_argument("--preview-path", default="release/v139_07/actual/order_launch_preview.json")
    p.add_argument("--preparation-token-path", default="release/v139_07/actual/order_submission_preparation_token.json")
    p.add_argument("--result-path", default="release/v139_07/actual/autonomous_paper_order_launch_result.json")
    p.add_argument("--approval-phrase", default="")
    p.add_argument("--enable-submission", action="store_true")
    a = p.parse_args()
    root = Path(a.repository_root).resolve()
    report = AutonomousPaperOrderLaunch().run(
        eligibility_result_path=root / a.eligibility_result_path,
        eligibility_token_path=root / a.eligibility_token_path,
        order_candidate_path=root / a.order_candidate_path,
        preview_path=root / a.preview_path,
        preparation_token_path=root / a.preparation_token_path,
        result_path=root / a.result_path,
        approval_phrase=a.approval_phrase,
        enable_submission=a.enable_submission,
    )
    print(json.dumps(report.to_json_dict(), indent=2, sort_keys=True))
    print(f"RESULT_FILE={(root / a.result_path).resolve()}")
    return 0 if report.status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
