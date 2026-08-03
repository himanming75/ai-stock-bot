from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
required=[
"v89_portfolio/io.py","v89_portfolio/scoring.py","v89_portfolio/sizing.py",
"v89_portfolio/risk.py","v89_portfolio/optimizer.py",
"tools/run_v89_33_to_v89_64.py","tools/test_v89_33_to_v89_64.py",
"tools/verify_v89_33_to_v89_64.py",
"release/v89_33_to_v89_64/input/portfolio_policy.json"
]
missing=[item for item in required if not (ROOT/item).exists()]
for item in missing: print("MISSING:",item)
if missing: raise SystemExit(1)
print("V89.33-V89.64 INSTALL CHECK PASS")
