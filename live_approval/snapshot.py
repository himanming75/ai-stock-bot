from __future__ import annotations
from pathlib import Path
from typing import Any
from live_approval.io import load_json

def load_fixture(root:Path)->dict[str,Any]:
    return load_json(root/"release/v166_01_to_v170_64/input/live_readonly_fixture.json")

def build(root:Path)->dict[str,Any]:
    fixture=load_fixture(root)
    account=fixture.get("account",{})
    positions=fixture.get("positions",[])
    orders=fixture.get("orders",[])
    return {
        "source":"LOCAL_READ_ONLY_FIXTURE",
        "account":account,
        "positions":positions,
        "orders":orders,
        "account_id_masked":account.get("account_id_masked","NOT_AVAILABLE"),
        "actual_live_network_attempted":False,
        "actual_live_write_attempted":False,
        "actual_live_orders_submitted":0,
    }
