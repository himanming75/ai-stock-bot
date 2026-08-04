from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

required=[
"fast_track_paper/io.py",
"fast_track_paper/source.py",
"fast_track_paper/orders.py",
"fast_track_paper/fills.py",
"fast_track_paper/positions.py",
"fast_track_paper/lifecycle.py",
"fast_track_paper/close.py",
"fast_track_paper/analytics.py",
"fast_track_paper/checkpoint.py",
"fast_track_paper/engine.py",
"fast_track_paper/dashboard.py",
"tools/run_v106_33_to_v108_64.py",
"tools/test_v106_33_to_v108_64.py",
"tools/verify_v106_33_to_v108_64.py",
"release/v106_33_to_v108_64/input/fast_track_paper_policy.json",
"release/v106_33_to_v108_64/input/paper_price_scenario.json",
]
missing=[item for item in required if not (ROOT/item).exists()]
for item in missing:
    print("MISSING:",item)
if missing:
    raise SystemExit(1)
print("V106.33-V108.64 INSTALL CHECK PASS")
