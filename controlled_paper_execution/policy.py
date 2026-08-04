from pathlib import Path
from .io import read_json
POLICY_PATH=Path("release/v361_01_to_v370_64/config/controlled_paper_execution_policy.json")
def load(root): return read_json(root/POLICY_PATH)
def validate(p):
    c={"paper_endpoint_only":p.get("paper_endpoint_only") is True,
       "live_endpoint_disabled":p.get("live_endpoint_enabled") is False,
       "paper_default_off":p.get("paper_submission_enabled") is False,
       "notional_safe":0<float(p.get("maximum_order_notional",0))<=1,
       "daily_limit_safe":int(p.get("maximum_daily_orders",0))==1,
       "symbol_allowlist":bool(p.get("allowed_symbols")),
       "market_only":p.get("allowed_order_types")==["market"],
       "day_only":p.get("allowed_time_in_force")==["day"]}
    return {"valid":all(c.values()),"checks":c,"failed":[k for k,v in c.items() if not v]}
