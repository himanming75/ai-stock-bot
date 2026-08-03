from __future__ import annotations
from pathlib import Path
from paper_account_ledger.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result = load_json(
        root / "release/v96_01_to_v96_32/actual/"
        "paper_account_reconciliation_result.json"
    )
    return {
        "paper_account_state": result.get("state", "NOT_AVAILABLE"),
        "cash_reconciliation": result.get("cash_reconciliation", {}),
        "position_reconciliation": result.get(
            "position_reconciliation", {}
        ),
        "equity_reconciliation": result.get(
            "equity_reconciliation", {}
        ),
        "realized_pnl": result.get("realized_pnl", 0.0),
        "unrealized_pnl": result.get("unrealized_pnl", 0.0),
        "total_pnl": result.get("total_pnl", 0.0),
        "integrity": result.get("integrity", {}),
        "paper_only": True,
    }
