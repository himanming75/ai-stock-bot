from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.terminal_commit_cycle_completion import (
    TerminalCommitCycleCompletion,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--lifecycle-result-path", default="release/v139_09/actual/active_order_lifecycle_monitor_result.json")
    parser.add_argument("--monitor-state-path", default="release/v139_09/actual/active_order_monitor_state.json")
    parser.add_argument("--terminal-commit-token-path", default="release/v139_10/actual/terminal_commit_token.json")
    parser.add_argument("--cycle-completion-token-path", default="release/v139_10/actual/cycle_completion_token.json")
    parser.add_argument("--completion-ledger-path", default="release/v139_10/actual/cycle_completion_ledger.jsonl")
    parser.add_argument("--audit-snapshot-path", default="release/v139_10/actual/cycle_completion_audit_snapshot.json")
    parser.add_argument("--result-path", default="release/v139_10/actual/terminal_commit_cycle_completion_result.json")
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()

    report = TerminalCommitCycleCompletion().run(
        lifecycle_result_path=root / args.lifecycle_result_path,
        monitor_state_path=root / args.monitor_state_path,
        terminal_commit_token_path=root / args.terminal_commit_token_path,
        cycle_completion_token_path=root / args.cycle_completion_token_path,
        completion_ledger_path=root / args.completion_ledger_path,
        audit_snapshot_path=root / args.audit_snapshot_path,
        result_path=root / args.result_path,
    )
    print(json.dumps(report.to_json_dict(), indent=2, sort_keys=True))
    print(f"RESULT_FILE={(root / args.result_path).resolve()}")
    return 0 if report.status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
