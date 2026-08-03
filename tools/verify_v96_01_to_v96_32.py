import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
path=(
    ROOT
    / "release/v96_01_to_v96_32/actual/"
    "paper_account_reconciliation_result.json"
)
if not path.exists():
    raise SystemExit("RESULT NOT FOUND")

result=json.loads(path.read_text())
checks={
"stage":result.get("stage_range")=="V96.01-V96.32",
"status":result.get("status")=="PASS",
"allowed_state":result.get("state") in {
"PAPER_ACCOUNT_LEDGER_SOURCE_REQUIRED",
"PAPER_ACCOUNT_RECONCILIATION_PASS",
"PAPER_ACCOUNT_RECONCILIATION_REVIEW_REQUIRED",
},
"hash_valid":(
    len(result.get("paper_account_certificate_sha256",""))==64
    if result.get("state")!="PAPER_ACCOUNT_LEDGER_SOURCE_REQUIRED"
    else True
),
"cash_entries_valid":isinstance(result.get("cash_ledger_entries",[]),list),
"position_entries_valid":isinstance(result.get("position_ledger_entries",[]),list),
"orders_zero":result.get("actual_orders_submitted")==0,
"paper_only":result.get("paper_only") is True,
"broker_write_disabled":result.get("broker_write_enabled") is False,
"orders_disabled":result.get("order_submission_enabled") is False,
"live_disabled":result.get("live_trading_enabled") is False,
"network_disabled":result.get("external_network_enabled") is False,
}
failed=[name for name,passed in checks.items() if not passed]
print(json.dumps({
"verification_stage":"V96.32",
"verification_status":"PASS" if not failed else "FAIL",
"state":result.get("state"),
"cash_reconciliation":result.get("cash_reconciliation"),
"position_reconciliation":result.get("position_reconciliation"),
"equity_reconciliation":result.get("equity_reconciliation"),
"duplicate_fill_ids":result.get("duplicate_fill_ids",[]),
"integrity":result.get("integrity"),
"total_pnl":result.get("total_pnl"),
"checks":checks,
"failed":failed,
},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
