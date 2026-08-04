from pathlib import Path
from order_lifecycle_v2.io import load_json

def payload(root: Path) -> dict:
    return load_json(root / "release/v231_01_to_v235_64/actual/order_lifecycle_v2_result.json")
