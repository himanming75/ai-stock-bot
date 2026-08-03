from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

required=[
"daily_paper_close/io.py",
"daily_paper_close/metrics.py",
"daily_paper_close/gates.py",
"daily_paper_close/report.py",
"daily_paper_close/engine.py",
"daily_paper_close/dashboard.py",
"tools/run_v96_33_to_v96_64.py",
"tools/test_v96_33_to_v96_64.py",
"tools/verify_v96_33_to_v96_64.py",
"release/v96_33_to_v96_64/input/daily_close_policy.json",
]
missing=[item for item in required if not (ROOT/item).exists()]
for item in missing:
    print("MISSING:",item)
if missing:
    raise SystemExit(1)

for dependency in (
    "paper_account_ledger",
    "paper_execution_simulator",
    "enterprise_risk_center",
):
    if not (ROOT/dependency).exists():
        print("MISSING DEPENDENCY:",dependency)
        raise SystemExit(1)

print("V96.33-V96.64 INSTALL CHECK PASS")
