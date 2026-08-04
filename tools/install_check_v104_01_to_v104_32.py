from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

required=[
"continuous_autonomous_engine/io.py",
"continuous_autonomous_engine/phases.py",
"continuous_autonomous_engine/source.py",
"continuous_autonomous_engine/session.py",
"continuous_autonomous_engine/gates.py",
"continuous_autonomous_engine/phase_executor.py",
"continuous_autonomous_engine/checkpoint.py",
"continuous_autonomous_engine/recovery.py",
"continuous_autonomous_engine/state.py",
"continuous_autonomous_engine/engine.py",
"continuous_autonomous_engine/dashboard.py",
"tools/run_v104_01_to_v104_32.py",
"tools/test_v104_01_to_v104_32.py",
"tools/verify_v104_01_to_v104_32.py",
"release/v104_01_to_v104_32/input/continuous_engine_policy.json",
]
missing=[item for item in required if not (ROOT/item).exists()]
for item in missing:
    print("MISSING:",item)
if missing:
    raise SystemExit(1)

print("V104.01-V104.32 INSTALL CHECK PASS")
