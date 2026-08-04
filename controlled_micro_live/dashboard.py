from pathlib import Path
from controlled_micro_live.io import load_json
def payload(root:Path)->dict:
    return load_json(root/"release/v171_01_to_v175_64/actual/controlled_micro_live_result.json")
