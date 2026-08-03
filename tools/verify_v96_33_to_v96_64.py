import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
path=(
    ROOT
    / "release/v96_33_to_v96_64/actual/"
    "daily_paper_close_result.json"
)
if not path.exists():
    raise SystemExit("RESULT NOT FOUND")

result=json.loads(path.read_text())
report=(
    ROOT
    / "release/v96_33_to_v96_64/actual/"
    "daily_paper_close_report.md"
)
checks={
"stage":result.get("stage_range")=="V96.33-V96.64",
"status":result.get("status")=="PASS",
"allowed_state":result.get("state") in {
"DAILY_PAPER_CLOSE_SOURCE_REQUIRED",
"DAILY_PAPER_CLOSE_COMPLETE",
"DAILY_PAPER_CLOSE_REVIEW_REQUIRED",
},
"hash_valid":(
    len(result.get("daily_close_certificate_sha256",""))==64
    if result.get("state")!="DAILY_PAPER_CLOSE_SOURCE_REQUIRED"
    else True
),
"report_exists":(
    report.exists()
    if result.get("state")!="DAILY_PAPER_CLOSE_SOURCE_REQUIRED"
    else True
),
"metrics_valid":isinstance(result.get("daily_metrics",{}),dict),
"fills_valid":isinstance(result.get("fill_summary",{}),dict),
"positions_valid":isinstance(result.get("position_summary",{}),dict),
"orders_zero":result.get("actual_orders_submitted")==0,
"paper_only":result.get("paper_only") is True,
"broker_write_disabled":result.get("broker_write_enabled") is False,
"orders_disabled":result.get("order_submission_enabled") is False,
"live_disabled":result.get("live_trading_enabled") is False,
"network_disabled":result.get("external_network_enabled") is False,
}
failed=[name for name,passed in checks.items() if not passed]
print(json.dumps({
"verification_stage":"V96.64",
"verification_status":"PASS" if not failed else "FAIL",
"state":result.get("state"),
"close_date":result.get("close_date"),
"daily_metrics":result.get("daily_metrics"),
"fill_summary":result.get("fill_summary"),
"position_summary":result.get("position_summary"),
"risk_summary":result.get("risk_summary"),
"account_summary":result.get("account_summary"),
"close_gates":result.get("close_gates"),
"checks":checks,
"failed":failed,
},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
