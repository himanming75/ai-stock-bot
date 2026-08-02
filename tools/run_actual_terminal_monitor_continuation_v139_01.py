from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from autonomous_paper_runtime.actual_terminal_monitor_continuation import ActualSavedStateTerminalMonitorContinuation


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repository-root", default=".")
    p.add_argument("--readiness-path", default="release/v139_00/actual/readiness.json")
    p.add_argument("--cycle-result-path", default="release/v139_00/actual/actual_autonomous_cycle_continuation_result.json")
    p.add_argument("--result-path", default="release/v139_01/actual/actual_terminal_monitor_continuation_result.json")
    a = p.parse_args()
    root = Path(a.repository_root).resolve()
    report = ActualSavedStateTerminalMonitorContinuation().run(
        readiness_path=root / a.readiness_path,
        cycle_result_path=root / a.cycle_result_path,
        result_path=root / a.result_path,
    )
    print(json.dumps(report.to_json_dict(), indent=2, sort_keys=True))
    print(f"RESULT_FILE={(root / a.result_path).resolve()}")
    return 0 if report.status == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
