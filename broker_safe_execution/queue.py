from __future__ import annotations
from typing import Any

def build_queue(
    intents: list[dict[str, Any]],
    validations: dict[str, Any],
    translated: list[dict[str, Any]],
) -> dict[str, Any]:
    validation_lookup={
        row.get("intent_id"):row for row in validations.get("rows",[])
    }
    translation_lookup={
        row.get("intent_id"):row for row in translated
    }
    rows=[]
    for intent in intents:
        intent_id=intent.get("intent_id")
        valid=validation_lookup.get(intent_id,{}).get("passed") is True
        rows.append({
            "intent_id":intent_id,
            "symbol":intent.get("symbol"),
            "side":intent.get("side"),
            "quantity":intent.get("quantity"),
            "validation_passed":valid,
            "translated_payload":translation_lookup.get(intent_id,{}),
            "state":"WAITING_FOR_MANUAL_APPROVAL" if valid else "REJECTED",
            "broker_submission_authorized":False,
            "submitted":False,
        })
    return {
        "queue_count":len(rows),
        "ready_for_approval_count":sum(
            1 for row in rows
            if row["state"]=="WAITING_FOR_MANUAL_APPROVAL"
        ),
        "rejected_count":sum(
            1 for row in rows if row["state"]=="REJECTED"
        ),
        "rows":rows,
    }
