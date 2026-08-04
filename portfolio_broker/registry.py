from __future__ import annotations
from pathlib import Path
from typing import Any
from portfolio_broker.io import load_json
from portfolio_broker.adapters import FixtureBrokerAdapter

def load_registry(root:Path)->dict[str,Any]:
    return load_json(root/"release/v181_01_to_v185_64/config/broker_registry.json")

def build_adapters(root:Path)->list[FixtureBrokerAdapter]:
    registry=load_registry(root)
    adapters=[]
    for row in registry.get("brokers",[]):
        if not row.get("enabled",True): continue
        fixture=load_json(root/row["fixture_path"])
        adapters.append(FixtureBrokerAdapter(str(row["broker_id"]),fixture))
    return adapters
