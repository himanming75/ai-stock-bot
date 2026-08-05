from __future__ import annotations


def validate_item(item: dict, policy: dict) -> list[str]:
    blockers = []
    request = item.get("broker_request", {}).get("request", {})

    if item.get("status") != "APPROVED_FOR_SEPARATE_SUBMISSION_STAGE":
        blockers.append("ITEM_NOT_APPROVED")
    if request.get("method") != "POST":
        blockers.append("METHOD_NOT_POST")
    if request.get("url") != "https://paper-api.alpaca.markets/v2/orders":
        blockers.append("NON_PAPER_ORDER_ENDPOINT")
    if request.get("submission_enabled") is not False:
        blockers.append("REQUEST_SUBMISSION_FLAG_MUST_BE_OFF")
    if request.get("broker_write_allowed") is not False:
        blockers.append("REQUEST_BROKER_WRITE_FLAG_MUST_BE_OFF")
    if not request.get("headers", {}).get("Idempotency-Key"):
        blockers.append("IDEMPOTENCY_HEADER_MISSING")
    if not request.get("json"):
        blockers.append("REQUEST_JSON_MISSING")
    if policy.get("engine_mode") != "dry_run":
        blockers.append("ENGINE_MODE_MUST_BE_DRY_RUN")
    if policy.get("network_enabled") is True:
        blockers.append("NETWORK_POLICY_MUST_BE_OFF")
    if policy.get("broker_write_enabled") is True:
        blockers.append("BROKER_WRITE_POLICY_MUST_BE_OFF")
    if policy.get("paper_submission_enabled") is True:
        blockers.append("PAPER_SUBMISSION_POLICY_MUST_BE_OFF")
    if policy.get("live_submission_enabled") is True:
        blockers.append("LIVE_SUBMISSION_POLICY_MUST_BE_OFF")
    return blockers
