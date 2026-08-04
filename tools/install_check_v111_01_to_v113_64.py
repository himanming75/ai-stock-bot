from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

required=[
"live_broker_readonly/io.py",
"live_broker_readonly/capabilities.py",
"live_broker_readonly/credentials.py",
"live_broker_readonly/adapters.py",
"live_broker_readonly/normalize.py",
"live_broker_readonly/reconcile.py",
"live_broker_readonly/drift.py",
"live_broker_readonly/boundary.py",
"live_broker_readonly/engine.py",
"live_broker_readonly/dashboard.py",
"tools/run_v111_01_to_v113_64.py",
"tools/test_v111_01_to_v113_64.py",
"tools/verify_v111_01_to_v113_64.py",
"release/v111_01_to_v113_64/input/live_broker_readonly_policy.json",
"release/v111_01_to_v113_64/input/broker_snapshot_fixture.json",
"release/v111_01_to_v113_64/docs/CREDENTIAL_SETUP_GUIDE.md",
]
missing=[item for item in required if not (ROOT/item).exists()]
for item in missing:
    print("MISSING:",item)
if missing:
    raise SystemExit(1)
print("V111.01-V113.64 INSTALL CHECK PASS")
