from pathlib import Path
from production_operations.io import load_json
def payload(root:Path)->dict:
    return load_json(root/"release/v186_01_to_v190_64/actual/production_operations_result.json")
