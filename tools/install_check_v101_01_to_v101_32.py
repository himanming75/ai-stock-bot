from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=['portfolio_rebalance_control/core.py','portfolio_rebalance_control/dashboard.py','tools/run_v101_01_to_v101_32.py','tools/test_v101_01_to_v101_32.py','tools/verify_v101_01_to_v101_32.py','release/v101_01_to_v101_32/input/rebalance_control_policy.json','release/v101_01_to_v101_32/input/current_strategy_weights.json']
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing:print('MISSING:',x)
if missing:raise SystemExit(1)
print('V101.01-V101.32 INSTALL CHECK PASS')
