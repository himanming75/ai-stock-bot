from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from autonomous_paper_runtime.runtime_control_bundle import RuntimeControlBundle

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repository-root", default=".")
    a = p.parse_args()
    root = Path(a.repository_root).resolve()
    result = RuntimeControlBundle().run(
        runtime_result_path=root/"release/v140_01/actual/autonomous_runtime_supervisor_result.json",
        runtime_token_path=root/"release/v140_01/actual/autonomous_runtime_token.json",
        market_snapshot_path=root/"release/v140_02_to_v140_05/input/market_session_snapshot.json",
        daily_risk_snapshot_path=root/"release/v140_02_to_v140_05/input/daily_risk_snapshot.json",
        health_snapshot_path=root/"release/v140_02_to_v140_05/input/runtime_health_snapshot.json",
        result_path=root/"release/v140_02_to_v140_05/actual/runtime_control_bundle_result.json",
        control_token_path=root/"release/v140_02_to_v140_05/actual/runtime_control_token.json",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"RESULT_FILE={result['result_path']}")
    return 0 if result["status"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
