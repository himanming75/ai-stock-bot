from pathlib import Path
import argparse, json, sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.shadow_daily_automation import (
    ShadowDailyAutomation,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()

    result = ShadowDailyAutomation().run(
        pipeline_result_path=root/"release/op2_13_to_op2_16/actual/automatic_shadow_signal_pipeline_result.json",
        runtime_policy_path=root/"release/op2_17_to_op2_20/input/shadow_runtime_policy.json",
        recovery_snapshot_path=root/"release/op2_17_to_op2_20/input/shadow_recovery_snapshot.json",
        daily_evidence_path=root/"release/op2_17_to_op2_20/input/daily_shadow_evidence.json",
        scheduler_state_path=root/"release/op2_17_to_op2_20/actual/shadow_runtime_scheduler_state.json",
        heartbeat_path=root/"release/op2_17_to_op2_20/actual/shadow_runtime_heartbeat.json",
        recovery_report_path=root/"release/op2_17_to_op2_20/actual/shadow_runtime_recovery_report.json",
        daily_report_path=root/"release/op2_17_to_op2_20/actual/daily_shadow_report.json",
        automation_token_path=root/"release/op2_17_to_op2_20/actual/shadow_daily_automation_token.json",
        result_path=root/"release/op2_17_to_op2_20/actual/shadow_daily_automation_result.json",
    )

    print(json.dumps(result, indent=2, sort_keys=True))
    print("RESULT_FILE=" + result["result_path"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
