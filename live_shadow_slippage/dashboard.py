from pathlib import Path
from live_shadow_slippage.io import load_json

def payload(root: Path) -> dict:
    return load_json(root / "release/v226_01_to_v230_64/actual/live_shadow_slippage_result.json")
