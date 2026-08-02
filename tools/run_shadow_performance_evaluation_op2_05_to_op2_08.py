from pathlib import Path
import argparse, json, sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.shadow_performance_evaluation import (
    ShadowPerformanceEvaluation,
)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repository-root", default=".")
    a = p.parse_args()
    root = Path(a.repository_root).resolve()

    result = ShadowPerformanceEvaluation().run(
        shadow_result_path=root/"release/op2_01_to_op2_04/actual/shadow_decision_bootstrap_result.json",
        evaluation_policy_path=root/"release/op2_05_to_op2_08/input/shadow_evaluation_policy.json",
        trade_evidence_path=root/"release/op2_05_to_op2_08/input/shadow_trade_evidence.json",
        trade_metrics_path=root/"release/op2_05_to_op2_08/actual/shadow_trade_metrics.json",
        equity_curve_path=root/"release/op2_05_to_op2_08/actual/shadow_equity_curve.json",
        performance_report_path=root/"release/op2_05_to_op2_08/actual/shadow_performance_report.json",
        evaluation_token_path=root/"release/op2_05_to_op2_08/actual/shadow_performance_token.json",
        result_path=root/"release/op2_05_to_op2_08/actual/shadow_performance_evaluation_result.json",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print("RESULT_FILE=" + result["result_path"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
