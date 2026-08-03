import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/"release/v94_01_to_v94_32/actual/meta_strategy_result.json"
if not p.exists(): raise SystemExit("RESULT NOT FOUND")
r=json.loads(p.read_text())
checks={
"stage":r.get("stage_range")=="V94.01-V94.32",
"status":r.get("status")=="PASS",
"allowed_state":r.get("state") in {
"META_STRATEGY_SOURCE_REQUIRED",
"META_STRATEGY_ENGINE_READY",
"META_STRATEGY_ENGINE_REVIEW_REQUIRED"},
"hash_valid":len(r.get("meta_strategy_certificate_sha256",""))==64 if r.get("state")!="META_STRATEGY_SOURCE_REQUIRED" else True,
"allocations_valid":isinstance(r.get("strategy_allocations",[]),list),
"rankings_valid":isinstance(r.get("strategy_rankings",[]),list),
"paper_only":r.get("paper_only") is True,
"broker_write_disabled":r.get("broker_write_enabled") is False,
"orders_disabled":r.get("order_submission_enabled") is False,
"live_disabled":r.get("live_trading_enabled") is False,
"network_disabled":r.get("external_network_enabled") is False,
}
failed=[k for k,v in checks.items() if not v]
selected=r.get("selected_strategy") or {}
print(json.dumps({
"verification_stage":"V94.32",
"verification_status":"PASS" if not failed else "FAIL",
"state":r.get("state"),
"paper_decision":r.get("paper_decision"),
"selected_strategy":selected,
"final_position_multiplier":r.get("final_position_multiplier"),
"failed_checks":r.get("failed_checks",[]),
"checks":checks,"failed":failed},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
