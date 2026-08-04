from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

required=[
"broker_safe_execution/io.py",
"broker_safe_execution/intents.py",
"broker_safe_execution/validation.py",
"broker_safe_execution/approval.py",
"broker_safe_execution/translators.py",
"broker_safe_execution/queue.py",
"broker_safe_execution/gateway.py",
"broker_safe_execution/sync.py",
"broker_safe_execution/engine.py",
"broker_safe_execution/dashboard.py",
"tools/run_v114_01_to_v116_64.py",
"tools/test_v114_01_to_v116_64.py",
"tools/verify_v114_01_to_v116_64.py",
"release/v114_01_to_v116_64/input/broker_safe_execution_policy.json",
"release/v114_01_to_v116_64/docs/MANUAL_APPROVAL_GUIDE.md",
]
missing=[item for item in required if not (ROOT/item).exists()]
for item in missing:
    print("MISSING:",item)
if missing:
    raise SystemExit(1)
print("V114.01-V116.64 INSTALL CHECK PASS")
