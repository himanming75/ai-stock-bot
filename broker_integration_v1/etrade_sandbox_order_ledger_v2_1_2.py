from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json


def account_fingerprint(account_id_key):
    return sha256(str(account_id_key).encode("utf-8")).hexdigest()[:16]


class SandboxOrderLedger:
    def __init__(self, root):
        self.path=Path(root)/"runtime"/"etrade_sandbox_order_v2_1_2"/"order_ledger.jsonl"

    def append(self,event):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        row=dict(event or {})
        row.setdefault("recorded_at_utc",datetime.now(timezone.utc).isoformat())
        with self.path.open("a",encoding="utf-8") as f:
            f.write(json.dumps(row,separators=(",",":"),ensure_ascii=False)+"\n")
        return row

    def record_preview(self,account_id_key,request,preview):
        return self.append({
            "event_type":"SANDBOX_PREVIEW",
            "account_fingerprint":account_fingerprint(account_id_key),
            "symbol":request.symbol,
            "side":request.side.value,
            "quantity":str(request.quantity),
            "order_type":request.order_type.value,
            "client_order_id":preview.get("client_order_id"),
            "preview_id":preview.get("preview_id"),
            "status":preview.get("status"),
            "real_money_moved":False,
            "production_order":False,
        })

    def record_place(self,account_id_key,request,place):
        return self.append({
            "event_type":"SANDBOX_PLACE",
            "account_fingerprint":account_fingerprint(account_id_key),
            "symbol":request.symbol,
            "side":request.side.value,
            "quantity":str(request.quantity),
            "order_type":request.order_type.value,
            "preview_id":place.get("preview_id"),
            "sandbox_order_id":place.get("order_id"),
            "status":place.get("status"),
            "real_money_moved":False,
            "production_order":False,
        })

    def record_reconciliation(self,account_id_key,result):
        return self.append({
            "event_type":"SANDBOX_RECONCILIATION",
            "account_fingerprint":account_fingerprint(account_id_key),
            "sandbox_order_id":result.get("sandbox_order_id"),
            "reconciliation_status":result.get("status"),
            "observed_order_count":result.get("observed_order_count",0),
            "matched_order_count":result.get("matched_order_count",0),
            "sandbox_sample_data_possible":True,
            "real_money_moved":False,
            "production_order":False,
        })
