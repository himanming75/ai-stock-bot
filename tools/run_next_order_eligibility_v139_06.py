from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.next_order_eligibility import NextOrderEligibility


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repository-root", default=".")
    p.add_argument("--cycle-result-path", default="release/v139_05/actual/autonomous_cycle_resume_result.json")
    p.add_argument("--eligibility-snapshot-path", default="release/v139_06/input/next_order_eligibility_snapshot.json")
    p.add_argument("--eligibility-token-path", default="release/v139_06/actual/next_order_eligibility_token.json")
    p.add_argument("--result-path", default="release/v139_06/actual/next_order_eligibility_result.json")
    a = p.parse_args()
    root = Path(a.repository_root).resolve()
    report = NextOrderEligibility().run(
        cycle_result_path=root / a.cycle_result_path,
        eligibility_snapshot_path=root / a.eligibility_snapshot_path,
        eligibility_token_path=root / a.eligibility_token_path,
        result_path=root / a.result_path,
    )
    print(json.dumps(report.to_json_dict(), indent=2, sort_keys=True))
    print(f"RESULT_FILE={(root / a.result_path).resolve()}")
    return 0 if report.status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
