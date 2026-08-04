import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
path=(
    ROOT/"release/v103_33_to_v103_64/actual/"
    "multi_day_scheduler_result.json"
)
if not path.exists():
    raise SystemExit("RESULT NOT FOUND")

result=json.loads(path.read_text(encoding="utf-8"))
checks={
"stage":result.get("stage_range")=="V103.33-V103.64",
"status":result.get("status")=="PASS",
"allowed_state":result.get("state") in {
"MULTI_DAY_SCHEDULER_READY",
"MULTI_DAY_SCHEDULER_SOURCE_REQUIRED",
"MULTI_DAY_SCHEDULER_DUPLICATE_REVIEW_REQUIRED",
"MULTI_DAY_SCHEDULER_NO_SESSIONS"},
"hash_valid":len(
    result.get("multi_day_scheduler_certificate_sha256","")
)==64,
"scheduler_id_valid":len(str(result.get("scheduler_id","")))==24,
"trading_days_valid":isinstance(
    result.get("scheduled_trading_days",[]),list
),
"queue_valid":isinstance(result.get("queue",{}),dict),
"summary_valid":isinstance(result.get("queue_summary",{}),dict),
"duplicate_valid":isinstance(
    result.get("duplicate_analysis",{}),dict
),
"checkpoint_valid":isinstance(result.get("checkpoint",{}),dict),
"resume_supported":result.get("resume_supported") is True,
"approval_not_granted":result.get("approval_granted") is False,
"execution_not_authorized":result.get("execution_authorized") is False,
"manual_approval_required":result.get("manual_approval_required") is True,
"credentials_unused":result.get("actual_credentials_used") is False,
"network_unused":result.get("actual_external_network_used") is False,
"orders_zero":result.get("actual_orders_submitted")==0,
"paper_only":result.get("paper_only") is True,
"broker_write_disabled":result.get("broker_write_enabled") is False,
"orders_disabled":result.get("order_submission_enabled") is False,
"live_disabled":result.get("live_trading_enabled") is False,
"network_disabled":result.get("external_network_enabled") is False,
}
failed=[name for name,passed in checks.items() if not passed]
print(json.dumps({
"verification_stage":"V103.64",
"verification_status":"PASS" if not failed else "FAIL",
"state":result.get("state"),
"scheduler_id":result.get("scheduler_id"),
"source_cycle_id":result.get("source_cycle_id"),
"requested_start_date":result.get("requested_start_date"),
"scheduled_trading_days":result.get("scheduled_trading_days"),
"queue_summary":result.get("queue_summary"),
"duplicate_analysis":result.get("duplicate_analysis"),
"checkpoint":result.get("checkpoint"),
"checks":checks,
"failed":failed,
},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
