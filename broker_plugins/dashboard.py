from pathlib import Path
from broker_plugins.io import load_json

def payload(root: Path) -> dict:
    return load_json(root / "release/v201_01_to_v205_64/actual/broker_plugin_framework_result.json")
