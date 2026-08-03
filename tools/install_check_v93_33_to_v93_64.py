from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
required=[
"multi_timeframe_regime/io.py","multi_timeframe_regime/resample.py",
"multi_timeframe_regime/frame_analysis.py","multi_timeframe_regime/consensus.py",
"multi_timeframe_regime/decision.py","multi_timeframe_regime/engine.py",
"multi_timeframe_regime/dashboard.py","tools/run_v93_33_to_v93_64.py",
"tools/test_v93_33_to_v93_64.py","tools/verify_v93_33_to_v93_64.py",
"release/v93_33_to_v93_64/input/multi_timeframe_policy.json",
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing: print("MISSING:",x)
if missing: raise SystemExit(1)
for dep in ("v89_engine","market_regime_engine"):
    if not (ROOT/dep).exists():
        print("MISSING DEPENDENCY:",dep); raise SystemExit(1)
print("V93.33-V93.64 INSTALL CHECK PASS")
