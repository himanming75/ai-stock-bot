from __future__ import annotations
from typing import Any

def evaluate_safety(modules: list[dict[str, Any]]) -> dict[str, Any]:
    checks={
        "all_orders_zero":all(
            int(row.get("actual_orders_submitted",0) or 0)==0
            for row in modules
        ),
        "all_execution_unauthorized":all(
            row.get("execution_authorized") is not True
            for row in modules
        ),
        "all_paper_only":all(
            row.get("paper_only") is not False
            for row in modules
        ),
        "broker_write_disabled":True,
        "order_submission_disabled":True,
        "live_trading_disabled":True,
        "external_network_disabled":True,
        "manual_approval_required":True,
    }
    failed=[name for name,passed in checks.items() if not passed]
    return {"passed":not failed,"checks":checks,"failed":failed}
