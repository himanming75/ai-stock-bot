from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from operations.daily_reporting import export_daily_report

parser = argparse.ArgumentParser()
parser.add_argument("--trading-day", default=None)
args = parser.parse_args()

result = export_daily_report(ROOT, trading_day=args.trading_day)
print(json.dumps({
    "json_path": result["json_path"],
    "csv_path": result["csv_path"],
    "trading_day": result["report"]["trading_day"],
    "timeline_record_count": result["report"]["timeline_record_count"],
    "actual_paper_orders_submitted": 0,
    "actual_live_orders_submitted": 0,
}, indent=2, sort_keys=True))
