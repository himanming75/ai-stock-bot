from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from shadow_trading.foundation_v81 import run_shadow_foundation
r=run_shadow_foundation(ROOT/"release/v80_01_to_v80_04/actual/paper_trading_completion_result.json",ROOT/"release/dash2_05/actual/current_paper_snapshot.json",ROOT/"release/op2_13_to_op2_16/actual/automatic_shadow_signal_pipeline_result.json",ROOT/"release/v81_01_to_v81_04/input/shadow_trading_policy.json",ROOT/"release/v81_01_to_v81_04/actual/shadow_trading_foundation_result.json",ROOT/"release/v81_01_to_v81_04/actual/shadow_trading_dashboard_state.json",ROOT/"release/v81_01_to_v81_04/actual/shadow_trade_observation.json")
print(json.dumps(r,indent=2,sort_keys=True)); print("RESULT_FILE="+r["result_path"])
raise SystemExit(0 if r["status"]=="PASS" else 2)
