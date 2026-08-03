from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
required=["v89_engine/io.py","v89_engine/discovery.py","v89_engine/strategies.py","v89_engine/backtest.py",
"v89_engine/gates.py","v89_engine/final_validation.py","v89_engine/engine.py","tools/run_v89_01_to_v89_32.py",
"tools/test_v89_01_to_v89_32.py","tools/verify_v89_01_to_v89_32.py"]
missing=[x for x in required if not (ROOT/x).exists()]
print("\n".join("MISSING: "+x for x in missing))
if missing: raise SystemExit(1)
print("V89.01-V89.32 INSTALL CHECK PASS")
