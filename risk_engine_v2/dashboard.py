from pathlib import Path
from risk_engine_v2.io import load_json
def payload(root:Path)->dict:
    return load_json(root/"release/v206_01_to_v210_64/actual/risk_engine_v2_result.json")
