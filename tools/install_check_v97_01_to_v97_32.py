from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

required=[
"paper_broker_adapter/io.py",
"paper_broker_adapter/base.py",
"paper_broker_adapter/mock.py",
"paper_broker_adapter/alpaca_readonly.py",
"paper_broker_adapter/ibkr_readonly.py",
"paper_broker_adapter/factory.py",
"paper_broker_adapter/translators.py",
"paper_broker_adapter/boundary.py",
"paper_broker_adapter/engine.py",
"paper_broker_adapter/dashboard.py",
"tools/run_v97_01_to_v97_32.py",
"tools/test_v97_01_to_v97_32.py",
"tools/verify_v97_01_to_v97_32.py",
"release/v97_01_to_v97_32/input/paper_broker_adapter_policy.json",
]
missing=[item for item in required if not (ROOT/item).exists()]
for item in missing:
    print("MISSING:",item)
if missing:
    raise SystemExit(1)

if not (ROOT/"daily_paper_close").exists():
    print("MISSING DEPENDENCY: daily_paper_close")
    raise SystemExit(1)

print("V97.01-V97.32 INSTALL CHECK PASS")
