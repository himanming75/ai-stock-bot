from __future__ import annotations
import hashlib
from pathlib import Path
from real_paper_micro_order.io import load_json, write_json

def client_order_id(root: Path, policy: dict) -> str:
    raw = "|".join([
        "V310",
        str(policy.get("symbol", "")).upper(),
        str(policy.get("side", "")).lower(),
        f"{float(policy.get('notional', 0)):.2f}",
    ])
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]
    return f"AISB-V310-{digest}"

def already_submitted(root: Path, client_id: str) -> bool:
    ledger = load_json(
        root / "release/v306_01_to_v310_64/actual/micro_order_submission_ledger.json"
    )
    return client_id in ledger.get("orders", {})

def record(root: Path, client_id: str, receipt: dict) -> None:
    path = root / "release/v306_01_to_v310_64/actual/micro_order_submission_ledger.json"
    ledger = load_json(path)
    orders = ledger.get("orders", {})
    orders[client_id] = receipt
    ledger["orders"] = orders
    write_json(path, ledger)
