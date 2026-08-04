from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from final_production_release.engine import evaluate
p=argparse.ArgumentParser();p.add_argument("--skip-bundle",action="store_true");a=p.parse_args()
r=evaluate(ROOT,create_release_bundle=not a.skip_bundle)
print(json.dumps({
 "stage":r["stage"],"state":r["state"],"status":r["status"],
 "final_release_ready":r["final_release_ready"],
 "development_complete":r["development_complete"],
 "present_stage_count":r["inventory"]["present_stage_count"],
 "expected_stage_count":r["inventory"]["expected_stage_count"],
 "integration_modules_present":r["integration"]["present_module_count"],
 "paper_trading_ready":r["paper_trading_ready"],
 "live_trading_ready":r["live_trading_ready"],
 "manual_live_activation_required":r["manual_live_activation_required"],
 "automatic_order_submission_enabled":False,
 "broker_write_enabled":False,
 "actual_live_orders_submitted":r["actual_live_orders_submitted"],
 "next_phase":r["next_phase"],
},indent=2,sort_keys=True))
