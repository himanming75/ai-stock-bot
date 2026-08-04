from pathlib import Path
from exit_manager_v2.io import load_json

def payload(root: Path) -> dict:
    return load_json(root / "release/v241_01_to_v245_64/actual/exit_manager_v2_result.json")
