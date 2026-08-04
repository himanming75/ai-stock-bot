from pathlib import Path
from paper_operations_v2.io import load_json

def payload(root: Path) -> dict:
    return load_json(root / "release/v221_01_to_v225_64/actual/paper_operations_v2_result.json")
