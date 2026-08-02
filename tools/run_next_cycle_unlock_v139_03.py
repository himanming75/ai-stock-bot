from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.next_cycle_unlock import NextCycleUnlock


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument(
        "--handoff-result-path",
        default="release/v139_02/actual/terminal_commit_handoff_result.json",
    )
    parser.add_argument(
        "--handoff-token-path",
        default="release/v139_02/actual/terminal_commit_handoff_token.json",
    )
    parser.add_argument(
        "--unlock-token-path",
        default="release/v139_03/actual/next_cycle_unlock_token.json",
    )
    parser.add_argument(
        "--unlock-ledger-path",
        default="release/v139_03/actual/next_cycle_unlock_ledger.jsonl",
    )
    parser.add_argument(
        "--recovery-snapshot-path",
        default="release/v139_03/actual/next_cycle_unlock_recovery.json",
    )
    parser.add_argument(
        "--result-path",
        default="release/v139_03/actual/next_cycle_unlock_result.json",
    )
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()

    report = NextCycleUnlock().run(
        handoff_result_path=root / args.handoff_result_path,
        handoff_token_path=root / args.handoff_token_path,
        unlock_token_path=root / args.unlock_token_path,
        unlock_ledger_path=root / args.unlock_ledger_path,
        recovery_snapshot_path=root / args.recovery_snapshot_path,
        result_path=root / args.result_path,
    )
    print(json.dumps(report.to_json_dict(), indent=2, sort_keys=True))
    print(f"RESULT_FILE={(root / args.result_path).resolve()}")
    return 0 if report.status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
