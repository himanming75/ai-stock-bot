from __future__ import annotations
from typing import Any

REQUIRED_FIELDS = {
    "plugin_id", "display_name", "version", "api_version",
    "enabled", "read_only", "supports_orders", "capabilities",
}

ALLOWED_CAPABILITIES = {
    "account_read", "positions_read", "orders_read", "market_clock_read",
    "paper_account", "live_account_read_only", "fractional_shares",
    "options_read", "crypto_read", "streaming_read",
}

def validate_manifest(value: dict[str, Any]) -> dict[str, Any]:
    errors = []
    missing = sorted(REQUIRED_FIELDS - set(value))
    if missing:
        errors.append("Missing fields: " + ", ".join(missing))
    if str(value.get("api_version", "")) != "1":
        errors.append("api_version must be 1.")
    if value.get("read_only") is not True:
        errors.append("read_only must remain true.")
    if value.get("supports_orders") is not False:
        errors.append("supports_orders must remain false.")
    capabilities = value.get("capabilities", [])
    if not isinstance(capabilities, list):
        errors.append("capabilities must be a list.")
        capabilities = []
    unknown = sorted(set(capabilities) - ALLOWED_CAPABILITIES)
    if unknown:
        errors.append("Unknown capabilities: " + ", ".join(unknown))
    return {"valid": not errors, "errors": errors}
