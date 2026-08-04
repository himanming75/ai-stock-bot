from pathlib import Path
from paper_qualification.io import load_json

def payload(root: Path) -> dict:
    return load_json(root / "release/v291_01_to_v300_64/actual/paper_qualification_result.json")
