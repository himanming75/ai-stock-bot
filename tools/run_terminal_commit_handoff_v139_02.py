from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.terminal_commit_handoff import TerminalCommitHandoff


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument(
        "--monitor-result-path",
        default="release/v139_01/actual/actual_terminal_monitor_continuation_result.json",
    )
    parser.add_argument(
        "--handoff-token-path",
        default="release/v139_02/actual/terminal_commit_handoff_token.json",
    )
    parser.add_argument(
        "--recovery-ledger-path",
        default="release/v139_02/actual/terminal_commit_handoff_recovery.jsonl",
    )
    parser.add_argument(
        "--result-path",
        default="release/v139_02/actual/terminal_commit_handoff_result.json",
    )
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()

    report = TerminalCommitHandoff().run(
        monitor_result_path=root / args.monitor_result_path,
        handoff_token_path=root / args.handoff_token_path,
        recovery_ledger_path=root / args.recovery_ledger_path,
        result_path=root / args.result_path,
    )
    print(json.dumps(report.to_json_dict(), indent=2, sort_keys=True))
    print(f"RESULT_FILE={(root / args.result_path).resolve()}")
    return 0 if report.status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
