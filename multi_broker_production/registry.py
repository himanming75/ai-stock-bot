from __future__ import annotations
from pathlib import Path
from typing import Any
from multi_broker_production.io import load_json

def load_registry(root:Path)->dict[str,Any]:
    return load_json(root/"release/v196_01_to_v200_64/config/multi_broker_registry.json")

def active_rows(root:Path)->list[dict[str,Any]]:
    return [x for x in load_registry(root).get("brokers",[]) if x.get("enabled",True)]
