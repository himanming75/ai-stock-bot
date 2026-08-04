from __future__ import annotations
from typing import Any

def compare(paper:dict[str,Any],live:dict[str,Any])->dict[str,Any]:
    pe=float(paper.get("equity",0) or 0)
    le=float(live.get("equity",0) or 0)
    pb=float(paper.get("buying_power",0) or 0)
    lb=float(live.get("buying_power",0) or 0)
    return {
        "paper_equity":pe,
        "live_equity":le,
        "equity_difference":round(le-pe,2),
        "paper_buying_power":pb,
        "live_buying_power":lb,
        "buying_power_difference":round(lb-pb,2),
        "same_account_detected":paper.get("account_id_masked")==live.get("account_id_masked") and bool(live.get("account_id_masked")),
    }
