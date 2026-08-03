from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
required=[
"market_regime_engine/io.py","market_regime_engine/indicators.py",
"market_regime_engine/classifier.py","market_regime_engine/strategy_mapping.py",
"market_regime_engine/engine.py","market_regime_engine/dashboard.py",
"tools/run_v93_01_to_v93_32.py","tools/test_v93_01_to_v93_32.py",
"tools/verify_v93_01_to_v93_32.py",
"release/v93_01_to_v93_32/input/market_regime_policy.json",
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing: print("MISSING:",x)
if missing: raise SystemExit(1)
for dep in ("v89_engine","enterprise_risk_center","strategy_lab"):
    if not (ROOT/dep).exists():
        print("MISSING DEPENDENCY:",dep); raise SystemExit(1)
print("V93.01-V93.32 INSTALL CHECK PASS")
