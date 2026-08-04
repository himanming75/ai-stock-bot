from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from broker_plugins.engine import evaluate
r=evaluate(ROOT)
print(json.dumps({
    "stage":r["stage"],
    "state":r["state"],
    "status":r["status"],
    "discovered_plugin_count":r["discovered_plugin_count"],
    "enabled_plugin_count":r["enabled_plugin_count"],
    "loadable_plugin_count":r["loadable_plugin_count"],
    "plugin_order_submission_enabled":r["plugin_order_submission_enabled"],
    "broker_write_enabled":r["broker_write_enabled"],
    "actual_live_orders_submitted":0,
    "next_phase":r["next_phase"],
},indent=2,sort_keys=True))
