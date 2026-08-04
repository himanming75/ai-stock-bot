from pathlib import Path
from position_manager_v2.io import load_json

def payload(root: Path) -> dict:
    return load_json(root / "release/v236_01_to_v240_64/actual/position_manager_v2_result.json")
