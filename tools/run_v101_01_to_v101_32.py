from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from portfolio_rebalance_control.core import evaluate
r=evaluate(ROOT)
print(json.dumps({'stage':r.get('stage'),'state':r.get('state'),'status':r.get('status'),'rebalance_control_id':r.get('rebalance_control_id'),'largest_absolute_drift_pct':r.get('snapshot',{}).get('largest_absolute_drift_pct'),'rebalance_required_count':r.get('snapshot',{}).get('rebalance_required_count'),'actionable_adjustment_count':r.get('actionable_adjustment_count',0),'projected_cash_pct':r.get('controls',{}).get('projected_cash_pct'),'used_turnover_pct':r.get('controls',{}).get('used_turnover_pct'),'gate_passed':r.get('rebalance_gate',{}).get('passed'),'execution_authorized':r.get('execution_authorized'),'actual_orders_submitted':r.get('actual_orders_submitted'),'paper_only':r.get('paper_only'),'next_phase':r.get('next_phase')},indent=2,sort_keys=True))
print('RESULT_FILE='+str((ROOT/'release/v101_01_to_v101_32/actual/portfolio_rebalance_control_result.json').resolve()))
