import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/"release/v93_01_to_v93_32/actual/market_regime_result.json"
if not p.exists(): raise SystemExit("RESULT NOT FOUND")
r=json.loads(p.read_text())
checks={
"stage":r.get("stage_range")=="V93.01-V93.32",
"status":r.get("status")=="PASS",
"allowed_state":r.get("state") in {
"MARKET_REGIME_HISTORICAL_DATA_REQUIRED",
"MARKET_REGIME_ENGINE_READY",
"MARKET_REGIME_ENGINE_REVIEW_REQUIRED"},
"hash_valid":len(r.get("regime_certificate_sha256",""))==64 if r.get("state")!="MARKET_REGIME_HISTORICAL_DATA_REQUIRED" else True,
"regime_valid":isinstance(r.get("regime",{}),dict),
"recommendations_valid":isinstance(r.get("recommended_strategies",[]),list),
"paper_only":r.get("paper_only") is True,
"broker_write_disabled":r.get("broker_write_enabled") is False,
"orders_disabled":r.get("order_submission_enabled") is False,
"live_disabled":r.get("live_trading_enabled") is False,
"network_disabled":r.get("external_network_enabled") is False,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({
"verification_stage":"V93.32",
"verification_status":"PASS" if not failed else "FAIL",
"state":r.get("state"),
"regime":r.get("regime"),
"recommended_strategies":r.get("recommended_strategies",[]),
"effective_position_multiplier":r.get("effective_position_multiplier"),
"failed_checks":r.get("failed_checks",[]),
"checks":checks,"failed":failed},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
