from pathlib import Path
import argparse, json, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from daily_paper_close.engine import evaluate

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--close-date",default="")
    args=parser.parse_args()

    result=evaluate(ROOT,args.close_date)
    metrics=result.get("daily_metrics",{})
    summary={
        "stage":result.get("stage"),
        "state":result.get("state"),
        "status":result.get("status"),
        "close_date":result.get("close_date"),
        "starting_equity":metrics.get("starting_equity"),
        "ending_equity":metrics.get("ending_equity"),
        "daily_pnl":metrics.get("daily_pnl"),
        "daily_return_pct":metrics.get("daily_return_pct"),
        "open_position_count":result.get(
            "position_summary", {}
        ).get("open_position_count"),
        "fill_count":result.get(
            "fill_summary", {}
        ).get("fill_count"),
        "risk_approved":result.get(
            "risk_summary", {}
        ).get("risk_approved"),
        "reconciliation_state":result.get(
            "account_summary", {}
        ).get("reconciliation_state"),
        "close_gate_passed":result.get(
            "close_gates", {}
        ).get("passed"),
        "actual_orders_submitted":result.get(
            "actual_orders_submitted"
        ),
        "paper_only":result.get("paper_only"),
        "next_phase":result.get("next_phase"),
    }
    print(json.dumps(summary,indent=2,sort_keys=True))
    print(
        "RESULT_FILE="
        + str(
            (
                ROOT
                / "release/v96_33_to_v96_64/actual/"
                "daily_paper_close_result.json"
            ).resolve()
        )
    )
    print(
        "REPORT_FILE="
        + str(
            (
                ROOT
                / "release/v96_33_to_v96_64/actual/"
                "daily_paper_close_report.md"
            ).resolve()
        )
    )
    return 0

if __name__=="__main__":
    raise SystemExit(main())
