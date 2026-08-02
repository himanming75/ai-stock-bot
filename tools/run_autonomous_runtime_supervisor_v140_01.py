from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.autonomous_runtime_supervisor import AutonomousRuntimeSupervisor


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repository-root", default=".")
    p.add_argument("--runtime-token-path", default="release/v140_01/actual/autonomous_runtime_token.json")
    p.add_argument("--supervisor-state-path", default="release/v140_01/actual/autonomous_runtime_supervisor_state.json")
    p.add_argument("--lock-path", default="release/v140_01/actual/autonomous_runtime_supervisor_lock.json")
    p.add_argument("--result-path", default="release/v140_01/actual/autonomous_runtime_supervisor_result.json")
    a = p.parse_args()
    root = Path(a.repository_root).resolve()
    result = AutonomousRuntimeSupervisor().run(
        repository_root=root,
        runtime_token_path=root / a.runtime_token_path,
        supervisor_state_path=root / a.supervisor_state_path,
        lock_path=root / a.lock_path,
        result_path=root / a.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"RESULT_FILE={(root / a.result_path).resolve()}")
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
