from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

required=[
"paper_account_ledger/io.py",
"paper_account_ledger/ledger.py",
"paper_account_ledger/reconciliation.py",
"paper_account_ledger/integrity.py",
"paper_account_ledger/engine.py",
"paper_account_ledger/dashboard.py",
"tools/run_v96_01_to_v96_32.py",
"tools/test_v96_01_to_v96_32.py",
"tools/verify_v96_01_to_v96_32.py",
"release/v96_01_to_v96_32/input/account_reconciliation_policy.json",
]
missing=[item for item in required if not (ROOT/item).exists()]
for item in missing:
    print("MISSING:",item)
if missing:
    raise SystemExit(1)

for dependency in (
    "paper_execution_simulator",
    "paper_position_lifecycle",
):
    if not (ROOT/dependency).exists():
        print("MISSING DEPENDENCY:",dependency)
        raise SystemExit(1)

print("V96.01-V96.32 INSTALL CHECK PASS")
