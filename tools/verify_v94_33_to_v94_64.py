import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/"release/v94_33_to_v94_64/actual/paper_execution_plan.json"
if not p.exists(): raise SystemExit("RESULT NOT FOUND")
r=json.loads(p.read_text())
checks={
"stage":r.get("stage_range")=="V94.33-V94.64",
"status":r.get("status")=="PASS",
"allowed_state":r.get("state") in {
"DECISION_ORCHESTRATION_SOURCE_REQUIRED",
"PAPER_EXECUTION_PLAN_READY_FOR_MANUAL_APPROVAL",
"PAPER_EXECUTION_PLAN_REVIEW_REQUIRED"},
"hash_valid":len(r.get("decision_orchestration_certificate_sha256",""))==64 if r.get("state")!="DECISION_ORCHESTRATION_SOURCE_REQUIRED" else True,
"plans_valid":isinstance(r.get("paper_order_plans",[]),list),
"checklist_valid":isinstance(r.get("pre_execution_checklist",[]),list),
"manual_approval_required":r.get("manual_approval_required") is True,
"execution_not_authorized":r.get("execution_authorized") is False,
"orders_zero":r.get("actual_orders_submitted")==0,
"paper_only":r.get("paper_only") is True,
"broker_write_disabled":r.get("broker_write_enabled") is False,
"orders_disabled":r.get("order_submission_enabled") is False,
"live_disabled":r.get("live_trading_enabled") is False,
"network_disabled":r.get("external_network_enabled") is False,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({
"verification_stage":"V94.64",
"verification_status":"PASS" if not failed else "FAIL",
"state":r.get("state"),
"gates":r.get("gates"),
"planned_order_count":sum(1 for x in r.get("paper_order_plans",[]) if x.get("state")=="PLANNED"),
"duplicate_block_count":sum(1 for x in r.get("paper_order_plans",[]) if x.get("state")=="BLOCKED_DUPLICATE"),
"manual_approval_required":r.get("manual_approval_required"),
"execution_authorized":r.get("execution_authorized"),
"checks":checks,"failed":failed},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
