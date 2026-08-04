from __future__ import annotations
from datetime import datetime,timezone
from typing import Any
from v140_autonomous_release.io import digest

def build(safety:dict[str,Any],summary:dict[str,Any])->dict[str,Any]:
    body={
        "certificate_type":"V140_FINAL_AUTONOMOUS_RELEASE_CERTIFICATE",
        "issued_at":datetime.now(timezone.utc).isoformat(),
        "release_passed":safety.get("passed") is True,
        "development_complete":safety.get("passed") is True,
        "paper_trading_ready":safety.get("passed") is True,
        "live_trading_ready":False,
        "live_execution_authorized":False,
        "actual_live_orders_submitted":0,
        "source_summary_hash":digest(summary),
    }
    body["certificate_sha256"]=digest(body)
    return body
