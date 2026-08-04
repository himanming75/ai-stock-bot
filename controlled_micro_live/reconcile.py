from __future__ import annotations
from typing import Any

def build_plan(candidate:dict[str,Any])->dict[str,Any]:
    return {
        "candidate_id":candidate.get("candidate_id"),
        "required_steps":[
            "READ_LIVE_ACCOUNT_BEFORE_ORDER",
            "VERIFY_NO_EXISTING_DUPLICATE_ORDER",
            "VERIFY_SYMBOL_POSITION",
            "VERIFY_BUYING_POWER",
            "SUBMIT_SINGLE_MICRO_ORDER_ONLY_AFTER_SEPARATE_RELEASE",
            "READ_ORDER_BY_ID",
            "VERIFY_FILL_OR_CANCEL",
            "READ_POSITION_AFTER_FILL",
            "WRITE_BROKER_RECONCILIATION_LEDGER",
        ],
        "automatic_submission_included":False,
        "actual_live_orders_submitted":0,
    }
