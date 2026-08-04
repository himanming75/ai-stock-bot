from __future__ import annotations
from pathlib import Path
from typing import Any
from paper_qualification.io import read_jsonl,load_json

def collect(root:Path)->dict[str,Any]:
    trade_paths=[
        root/"release/v106_33_to_v108_64/actual/paper_exit_ledger.jsonl",
        root/"release/v124_01_to_v126_64/actual/paper_trade_ledger.jsonl",
        root/"release/v137_01_to_v139_64/actual/paper_trade_ledger.jsonl",
    ]
    daily_paths=[
        root/"release/v106_33_to_v108_64/actual/daily_performance_ledger.jsonl",
        root/"release/v137_01_to_v139_64/actual/autonomous_cycle_ledger.jsonl",
    ]
    trades=[]
    for p in trade_paths: trades.extend(read_jsonl(p))
    daily=[]
    for p in daily_paths: daily.extend(read_jsonl(p))
    orders=load_json(root/"release/v121_01_to_v123_64/actual/alpaca_paper_operations_result.json").get("order_snapshot",[])
    return {"trades":trades,"daily":daily,"orders":orders}
