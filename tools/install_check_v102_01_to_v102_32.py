from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

required = [
    "master_ai_orchestrator/io.py",
    "master_ai_orchestrator/registry.py",
    "master_ai_orchestrator/dependencies.py",
    "master_ai_orchestrator/workflow.py",
    "master_ai_orchestrator/safety.py",
    "master_ai_orchestrator/health.py",
    "master_ai_orchestrator/checkpoint.py",
    "master_ai_orchestrator/recovery.py",
    "master_ai_orchestrator/engine.py",
    "master_ai_orchestrator/dashboard.py",
    "tools/run_v102_01_to_v102_32.py",
    "tools/test_v102_01_to_v102_32.py",
    "tools/verify_v102_01_to_v102_32.py",
    "release/v102_01_to_v102_32/input/master_orchestrator_policy.json",
]
missing = [item for item in required if not (ROOT / item).exists()]
for item in missing:
    print("MISSING:", item)
if missing:
    raise SystemExit(1)

print("V102.01-V102.32 INSTALL CHECK PASS")
