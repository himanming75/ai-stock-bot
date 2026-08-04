from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from production_operations.engine import evaluate
p=argparse.ArgumentParser();p.add_argument("--skip-backup",action="store_true");a=p.parse_args()
r=evaluate(ROOT,create_backup=not a.skip_backup)
print(json.dumps({
 "stage":r["stage"],"state":r["state"],"status":r["status"],
 "health_status":r["health"]["status"],
 "daily_observations":r["reports"]["daily"]["observation_count"],
 "weekly_observations":r["reports"]["weekly"]["observation_count"],
 "monthly_observations":r["reports"]["monthly"]["observation_count"],
 "backup_file_count":r["backup"].get("file_count",0),
 "reporting_ready":r["reporting_ready"],
 "broker_write_enabled":r["broker_write_enabled"],
 "actual_live_orders_submitted":0,
 "next_phase":r["next_phase"]
},indent=2,sort_keys=True))
