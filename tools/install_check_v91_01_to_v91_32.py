from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
required=[
"strategy_lab/io.py","strategy_lab/registry.py","strategy_lab/adapter.py",
"strategy_lab/scoring.py","strategy_lab/engine.py","strategy_lab/dashboard.py",
"tools/run_v91_01_to_v91_32.py","tools/test_v91_01_to_v91_32.py",
"tools/verify_v91_01_to_v91_32.py"
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing:print("MISSING:",x)
if missing:raise SystemExit(1)
for module in ("v89_engine","dashboard_analytics_v3"):
    if not (ROOT/module).exists():
        print("MISSING DEPENDENCY:",module);raise SystemExit(1)
print("V91.01-V91.32 INSTALL CHECK PASS")
