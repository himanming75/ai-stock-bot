import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/"release/v95_33_to_v95_64/actual/paper_position_lifecycle_result.json"
if not p.exists(): raise SystemExit("RESULT NOT FOUND")
r=json.loads(p.read_text())
checks={
"stage":r.get("stage_range")=="V95.33-V95.64",
"status":r.get("status")=="PASS",
"allowed_state":r.get("state") in {
"PAPER_POSITION_LIFECYCLE_SOURCE_REQUIRED",
"PAPER_POSITION_LIFECYCLE_EXIT_ACTIONS_READY",
"PAPER_POSITION_LIFECYCLE_HOLD"},
"hash_valid":len(r.get("position_lifecycle_certificate_sha256",""))==64 if r.get("state")!="PAPER_POSITION_LIFECYCLE_SOURCE_REQUIRED" else True,
"decisions_valid":isinstance(r.get("position_decisions",[]),list),
"close_records_valid":isinstance(r.get("close_records",[]),list),
"orders_zero":r.get("actual_orders_submitted")==0,
"paper_only":r.get("paper_only") is True,
"broker_write_disabled":r.get("broker_write_enabled") is False,
"orders_disabled":r.get("order_submission_enabled") is False,
"live_disabled":r.get("live_trading_enabled") is False,
"network_disabled":r.get("external_network_enabled") is False,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({
"verification_stage":"V95.64",
"verification_status":"PASS" if not failed else "FAIL",
"state":r.get("state"),
"lifecycle_date":r.get("lifecycle_date"),
"open_position_count":r.get("open_position_count"),
"closed_position_count":r.get("closed_position_count"),
"total_realized_pnl":r.get("total_realized_pnl"),
"checks":checks,"failed":failed},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
