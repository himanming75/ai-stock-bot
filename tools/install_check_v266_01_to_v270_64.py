from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
required = [
    "windows_autostart_recovery/io.py",
    "windows_autostart_recovery/config.py",
    "windows_autostart_recovery/recovery.py",
    "windows_autostart_recovery/stale_lock.py",
    "windows_autostart_recovery/logs.py",
    "windows_autostart_recovery/supervisor.py",
    "windows_autostart_recovery/dashboard.py",
    "web_controller/windows_autostart_recovery_api.py",
    "tools/run_v266_01_to_v270_64.py",
    "tools/test_v266_01_to_v270_64.py",
    "tools/verify_v266_01_to_v270_64.py",
    "release/v266_01_to_v270_64/config/windows_autostart_recovery_policy.json",
    "release/v266_01_to_v270_64/docs/WINDOWS_AUTOSTART_RECOVERY_GUIDE.md",
]
missing = [item for item in required if not (ROOT / item).exists()]
for item in missing:
    print("MISSING:", item)
if missing:
    raise SystemExit(1)
print("V266.01-V270.64 INSTALL CHECK PASS")
