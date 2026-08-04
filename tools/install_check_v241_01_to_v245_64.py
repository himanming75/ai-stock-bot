from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
required = [
    "exit_manager_v2/io.py",
    "exit_manager_v2/config.py",
    "exit_manager_v2/rules.py",
    "exit_manager_v2/priority.py",
    "exit_manager_v2/scale_out.py",
    "exit_manager_v2/recovery.py",
    "exit_manager_v2/engine.py",
    "exit_manager_v2/dashboard.py",
    "web_controller/exit_manager_v2_api.py",
    "tools/run_v241_01_to_v245_64.py",
    "tools/test_v241_01_to_v245_64.py",
    "tools/verify_v241_01_to_v245_64.py",
    "release/v241_01_to_v245_64/config/exit_manager_v2_policy.json",
    "release/v241_01_to_v245_64/docs/EXIT_MANAGER_V2_GUIDE.md",
]
missing = [x for x in required if not (ROOT / x).exists()]
for x in missing:
    print("MISSING:", x)
if missing:
    raise SystemExit(1)
print("V241.01-V245.64 INSTALL CHECK PASS")
