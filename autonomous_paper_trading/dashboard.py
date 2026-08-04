from pathlib import Path
from autonomous_paper_trading.io import load_json

def payload(root: Path) -> dict:
    return load_json(root / "release/v256_01_to_v260_64/actual/autonomous_paper_trading_result.json")
