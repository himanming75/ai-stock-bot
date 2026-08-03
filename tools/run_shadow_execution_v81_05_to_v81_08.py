from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from shadow_trading.execution_engine_v81_05_08 import run_shadow_execution
r=run_shadow_execution(ROOT/"release/v81_01_to_v81_04/actual/shadow_trading_foundation_result.json",ROOT/"release/v81_01_to_v81_04/actual/shadow_trade_observation.json",ROOT/"release/v81_05_to_v81_08/input/shadow_execution_policy.json",ROOT/"release/v81_05_to_v81_08/actual/shadow_order_ledger.jsonl",ROOT/"release/v81_05_to_v81_08/actual/shadow_fill_ledger.jsonl",ROOT/"release/v81_05_to_v81_08/actual/shadow_execution_report.json",ROOT/"release/v81_05_to_v81_08/actual/shadow_execution_dashboard_state.json",ROOT/"release/v81_05_to_v81_08/actual/shadow_execution_result.json")
print(json.dumps(r,indent=2,sort_keys=True)); print("RESULT_FILE="+r["result_path"]); raise SystemExit(0 if r["status"]=="PASS" else 2)
