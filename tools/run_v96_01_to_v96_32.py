from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from paper_account_ledger.engine import evaluate

def main():
    result=evaluate(ROOT)
    summary={
        "stage":result.get("stage"),
        "state":result.get("state"),
        "status":result.get("status"),
        "source_simulation_cycle_id":result.get("source_simulation_cycle_id"),
        "cash_reconciled":result.get("cash_reconciliation",{}).get("passed"),
        "positions_reconciled":result.get("position_reconciliation",{}).get("passed"),
        "equity_reconciled":result.get("equity_reconciliation",{}).get("passed"),
        "duplicate_fill_count":len(result.get("duplicate_fill_ids",[])),
        "realized_pnl":result.get("realized_pnl"),
        "unrealized_pnl":result.get("unrealized_pnl"),
        "total_pnl":result.get("total_pnl"),
        "integrity_passed":result.get("integrity",{}).get("passed"),
        "actual_orders_submitted":result.get("actual_orders_submitted"),
        "paper_only":result.get("paper_only"),
        "next_phase":result.get("next_phase"),
    }
    print(json.dumps(summary,indent=2,sort_keys=True))
    print(
        "RESULT_FILE="
        + str(
            (
                ROOT
                / "release/v96_01_to_v96_32/actual/"
                "paper_account_reconciliation_result.json"
            ).resolve()
        )
    )
    return 0

if __name__=="__main__":
    raise SystemExit(main())
