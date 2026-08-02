from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.ultra_fast_cycle_finalization import UltraFastCycleFinalization


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repository-root", default=".")
    p.add_argument("--completion-result-path", default="release/v139_10/actual/terminal_commit_cycle_completion_result.json")
    p.add_argument("--completion-token-path", default="release/v139_10/actual/cycle_completion_token.json")
    p.add_argument("--terminal-token-path", default="release/v139_10/actual/terminal_commit_token.json")
    p.add_argument("--portfolio-snapshot-path", default="release/v139_11_to_v139_15/input/portfolio_reconciliation_snapshot.json")
    p.add_argument("--reconciliation-result-path", default="release/v139_11_to_v139_15/actual/portfolio_reconciliation_result.json")
    p.add_argument("--pnl-result-path", default="release/v139_11_to_v139_15/actual/pnl_settlement_result.json")
    p.add_argument("--execution-ledger-path", default="release/v139_11_to_v139_15/actual/execution_ledger_finalized.jsonl")
    p.add_argument("--archive-manifest-path", default="release/v139_11_to_v139_15/actual/cycle_archive_manifest.json")
    p.add_argument("--bootstrap-token-path", default="release/v139_11_to_v139_15/actual/next_cycle_bootstrap_token.json")
    p.add_argument("--result-path", default="release/v139_11_to_v139_15/actual/ultra_fast_cycle_finalization_result.json")
    a = p.parse_args()
    root = Path(a.repository_root).resolve()

    result = UltraFastCycleFinalization().run(
        completion_result_path=root / a.completion_result_path,
        completion_token_path=root / a.completion_token_path,
        terminal_token_path=root / a.terminal_token_path,
        portfolio_snapshot_path=root / a.portfolio_snapshot_path,
        reconciliation_result_path=root / a.reconciliation_result_path,
        pnl_result_path=root / a.pnl_result_path,
        execution_ledger_path=root / a.execution_ledger_path,
        archive_manifest_path=root / a.archive_manifest_path,
        bootstrap_token_path=root / a.bootstrap_token_path,
        result_path=root / a.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"RESULT_FILE={(root / a.result_path).resolve()}")
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
