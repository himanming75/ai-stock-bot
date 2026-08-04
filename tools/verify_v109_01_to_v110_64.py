import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
path=(
    ROOT/"release/v109_01_to_v110_64/actual/"
    "autonomous_paper_operations_result.json"
)
if not path.exists():
    raise SystemExit("RESULT NOT FOUND")

result=json.loads(path.read_text(encoding="utf-8"))
checks={
"stage":result.get("stage_range")=="V109.01-V110.64",
"status":result.get("status")=="PASS",
"allowed_state":result.get("state") in {
"AUTONOMOUS_PAPER_OPERATIONS_READY",
"AUTONOMOUS_PAPER_OPERATIONS_REVIEW_REQUIRED",
"AUTONOMOUS_PAPER_OPERATIONS_SOURCE_REQUIRED"},
"hash_valid":len(result.get("certificate_sha256",""))==64,
"tournament_valid":isinstance(result.get("tournament",{}),dict)
    if result.get("state")!="AUTONOMOUS_PAPER_OPERATIONS_SOURCE_REQUIRED"
    else True,
"sessions_valid":isinstance(result.get("sessions",[]),list)
    if result.get("state")!="AUTONOMOUS_PAPER_OPERATIONS_SOURCE_REQUIRED"
    else True,
"report_valid":isinstance(result.get("operations_report",{}),dict)
    if result.get("state")!="AUTONOMOUS_PAPER_OPERATIONS_SOURCE_REQUIRED"
    else True,
"orders_zero":result.get("actual_orders_submitted")==0,
"paper_only":result.get("paper_only") is True,
"live_execution_disabled":result.get("live_execution_authorized",False) is False,
"broker_submission_disabled":result.get("broker_submission_authorized",False) is False,
"broker_write_disabled":result.get("broker_write_enabled",False) is False,
"order_submission_disabled":result.get("order_submission_enabled",False) is False,
"live_disabled":result.get("live_trading_enabled") is False,
"network_disabled":result.get("external_network_enabled",False) is False,
"credentials_unused":result.get("actual_credentials_used",False) is False,
"network_unused":result.get("actual_external_network_used",False) is False,
"windows_task_not_installed":result.get("windows_task_installed",False) is False,
}
failed=[name for name,passed in checks.items() if not passed]
print(json.dumps({
"verification_stage":"V110.64",
"verification_status":"PASS" if not failed else "FAIL",
"state":result.get("state"),
"operations_id":result.get("operations_id"),
"tournament":result.get("tournament"),
"operations_report":result.get("operations_report"),
"sessions":result.get("sessions"),
"backups":result.get("backups"),
"checks":checks,
"failed":failed,
},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
