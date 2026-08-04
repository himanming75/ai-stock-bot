from pathlib import Path
from portfolio_broker.io import load_json
def payload(root:Path)->dict:
    return load_json(root/"release/v181_01_to_v185_64/actual/portfolio_broker_result.json")
