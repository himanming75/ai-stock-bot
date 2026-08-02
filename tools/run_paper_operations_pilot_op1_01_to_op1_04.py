from pathlib import Path
import argparse, json, sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.paper_operations_pilot import PaperOperationsPilot, PAPER_BASE_URL

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repository-root", default=".")
    p.add_argument("--enable-network", action="store_true")
    p.add_argument("--base-url", default=PAPER_BASE_URL)
    a = p.parse_args()
    root = Path(a.repository_root).resolve()
    result = PaperOperationsPilot().run(
        final_release_result_path=root/"release/v143_final/actual/final_production_release_result.json",
        pilot_policy_path=root/"release/op1_01_to_op1_04/input/pilot_policy.json",
        local_snapshot_path=root/"release/op1_01_to_op1_04/input/local_paper_snapshot.json",
        account_snapshot_path=root/"release/op1_01_to_op1_04/actual/paper_account_snapshot.json",
        preflight_report_path=root/"release/op1_01_to_op1_04/actual/pilot_preflight_report.json",
        pilot_token_path=root/"release/op1_01_to_op1_04/actual/paper_operations_pilot_token.json",
        result_path=root/"release/op1_01_to_op1_04/actual/paper_operations_pilot_result.json",
        base_url=a.base_url,
        enable_network=a.enable_network,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print("RESULT_FILE=" + result["result_path"])
    return 0 if result["status"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
