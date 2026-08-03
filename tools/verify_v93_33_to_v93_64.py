import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/"release/v93_33_to_v93_64/actual/multi_timeframe_regime_result.json"
if not p.exists(): raise SystemExit("RESULT NOT FOUND")
r=json.loads(p.read_text())
checks={
"stage":r.get("stage_range")=="V93.33-V93.64",
"status":r.get("status")=="PASS",
"allowed_state":r.get("state") in {
"MULTI_TIMEFRAME_HISTORICAL_DATA_REQUIRED",
"MULTI_TIMEFRAME_REGIME_READY",
"MULTI_TIMEFRAME_REGIME_REVIEW_REQUIRED"},
"hash_valid":len(r.get("multi_timeframe_certificate_sha256",""))==64 if r.get("state")!="MULTI_TIMEFRAME_HISTORICAL_DATA_REQUIRED" else True,
"frames_valid":isinstance(r.get("frames",[]),list),
"consensus_valid":isinstance(r.get("consensus",{}),dict),
"recommendations_valid":isinstance(r.get("recommended_strategies",[]),list),
"paper_only":r.get("paper_only") is True,
"broker_write_disabled":r.get("broker_write_enabled") is False,
"orders_disabled":r.get("order_submission_enabled") is False,
"live_disabled":r.get("live_trading_enabled") is False,
"network_disabled":r.get("external_network_enabled") is False,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({
"verification_stage":"V93.64",
"verification_status":"PASS" if not failed else "FAIL",
"state":r.get("state"),
"frame_count":r.get("frame_count"),
"consensus":r.get("consensus"),
"recommended_strategies":r.get("recommended_strategies",[]),
"effective_position_multiplier":r.get("effective_position_multiplier"),
"failed_checks":r.get("failed_checks",[]),
"checks":checks,"failed":failed},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
