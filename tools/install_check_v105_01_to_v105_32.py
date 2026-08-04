from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

required=[
"final_system_integration/io.py",
"final_system_integration/registry.py",
"final_system_integration/pipeline.py",
"final_system_integration/safety.py",
"final_system_integration/readiness.py",
"final_system_integration/checkpoint.py",
"final_system_integration/dashboard.py",
"final_system_integration/engine.py",
"tools/run_v105_01_to_v105_32.py",
"tools/test_v105_01_to_v105_32.py",
"tools/verify_v105_01_to_v105_32.py",
"release/v105_01_to_v105_32/input/final_integration_policy.json",
]
missing=[item for item in required if not (ROOT/item).exists()]
for item in missing:
    print("MISSING:",item)
if missing:
    raise SystemExit(1)

print("V105.01-V105.32 INSTALL CHECK PASS")
