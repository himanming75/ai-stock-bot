from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

required=[
"paper_broker_read_model/io.py",
"paper_broker_read_model/models.py",
"paper_broker_read_model/reconciliation.py",
"paper_broker_read_model/freshness.py",
"paper_broker_read_model/integrity.py",
"paper_broker_read_model/engine.py",
"paper_broker_read_model/dashboard.py",
"tools/run_v97_33_to_v97_64.py",
"tools/test_v97_33_to_v97_64.py",
"tools/verify_v97_33_to_v97_64.py",
"release/v97_33_to_v97_64/input/paper_broker_read_model_policy.json",
]
missing=[item for item in required if not (ROOT/item).exists()]
for item in missing:
    print("MISSING:",item)
if missing:
    raise SystemExit(1)

for dependency in (
    "paper_broker_adapter",
    "paper_account_ledger",
):
    if not (ROOT/dependency).exists():
        print("MISSING DEPENDENCY:",dependency)
        raise SystemExit(1)

print("V97.33-V97.64 INSTALL CHECK PASS")
