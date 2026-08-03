from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
required=[
"meta_strategy_engine/io.py","meta_strategy_engine/scoring.py",
"meta_strategy_engine/allocation.py","meta_strategy_engine/decision.py",
"meta_strategy_engine/engine.py","meta_strategy_engine/dashboard.py",
"tools/run_v94_01_to_v94_32.py","tools/test_v94_01_to_v94_32.py",
"tools/verify_v94_01_to_v94_32.py",
"release/v94_01_to_v94_32/input/meta_strategy_policy.json",
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing: print("MISSING:",x)
if missing: raise SystemExit(1)
for dep in ("strategy_lab","parameter_optimizer","enterprise_risk_center","multi_timeframe_regime","ai_explainability_pro"):
    if not (ROOT/dep).exists():
        print("MISSING DEPENDENCY:",dep); raise SystemExit(1)
print("V94.01-V94.32 INSTALL CHECK PASS")
