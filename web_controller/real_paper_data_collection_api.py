from pathlib import Path
from real_paper_data_collection.collector import collect
from real_paper_data_collection.io import load_json

def get_payload(root: Path) -> dict:
    return load_json(
        root / "release/v311_01_to_v320_64/actual/real_paper_data_collection_result.json"
    )

def refresh_read_only(root: Path) -> dict:
    return {"ok": True, "result": collect(root, allow_network=True)}
