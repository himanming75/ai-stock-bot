from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.autonomous_cycle_resume import AutonomousCycleResume


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repository-root", default=".")
    p.add_argument("--recovery-result-path", default="release/v139_04/actual/recovery_validation_result.json")
    p.add_argument("--resume-token-path", default="release/v139_05/actual/autonomous_cycle_resume_token.json")
    p.add_argument("--cycle-ledger-path", default="release/v139_05/actual/autonomous_cycle_resume_ledger.jsonl")
    p.add_argument("--recovery-snapshot-path", default="release/v139_05/actual/autonomous_cycle_resume_recovery.json")
    p.add_argument("--result-path", default="release/v139_05/actual/autonomous_cycle_resume_result.json")
    a = p.parse_args()
    root = Path(a.repository_root).resolve()
    report = AutonomousCycleResume().run(
        recovery_result_path=root / a.recovery_result_path,
        resume_token_path=root / a.resume_token_path,
        cycle_ledger_path=root / a.cycle_ledger_path,
        recovery_snapshot_path=root / a.recovery_snapshot_path,
        result_path=root / a.result_path,
    )
    print(json.dumps(report.to_json_dict(), indent=2, sort_keys=True))
    print(f"RESULT_FILE={(root / a.result_path).resolve()}")
    return 0 if report.status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
