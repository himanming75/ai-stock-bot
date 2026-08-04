from pathlib import Path
from ai_strategy_ensemble_v3.io import load_json

def payload(root: Path) -> dict:
    return load_json(root / "release/v246_01_to_v250_64/actual/ai_strategy_ensemble_v3_result.json")
