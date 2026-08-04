from pathlib import Path
from multi_timeframe_strategy.io import load_json

def payload(root: Path) -> dict:
    return load_json(root / "release/v271_01_to_v280_64/actual/multi_timeframe_strategy_result.json")
