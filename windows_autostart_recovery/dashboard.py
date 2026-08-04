from pathlib import Path
from windows_autostart_recovery.io import load_json

def payload(root: Path) -> dict:
    return load_json(root / "release/v266_01_to_v270_64/actual/windows_autostart_recovery_result.json")
