from pathlib import Path
from execution_optimizer.io import load_json

def payload(root: Path) -> dict:
    return load_json(root / "release/v251_01_to_v255_64/actual/execution_optimizer_result.json")
