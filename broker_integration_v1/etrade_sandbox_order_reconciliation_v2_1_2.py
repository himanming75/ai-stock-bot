from __future__ import annotations


def _order_rows(payload):
    body=(payload or {}).get("OrdersResponse") or payload or {}
    rows=body.get("Order") or body.get("order") or []
    if isinstance(rows,dict):
        rows=[rows]
    return rows if isinstance(rows,list) else []


def reconcile_sandbox_place(place_result,orders_payload):
    target=str((place_result or {}).get("order_id") or "")
    rows=_order_rows(orders_payload)

    matches=[]
    for row in rows:
        oid=row.get("orderId")
        if oid is not None and str(oid)==target:
            matches.append(row)

    if matches:
        status="MATCHED"
    elif rows:
        status="SAMPLE_DATA_MISMATCH"
    else:
        status="NOT_OBSERVED"

    return {
        "status":status,
        "sandbox_order_id":target or None,
        "observed_order_count":len(rows),
        "matched_order_count":len(matches),
        "matched_orders":matches,
        "sandbox_sample_data_possible":True,
        "profitability_validation":False,
        "real_execution_validation":False,
    }
