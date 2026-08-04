from pathlib import Path
from multi_broker_production.io import load_json
def payload(root:Path)->dict:
    return load_json(root/"release/v196_01_to_v200_64/actual/multi_broker_production_result.json")
