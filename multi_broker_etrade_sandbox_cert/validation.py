from __future__ import annotations
from .contracts import CONTRACTS

def validate_payloads(payloads: dict[str, dict]) -> list[dict]:
    out=[]
    for spec in CONTRACTS:
        payload=payloads.get(spec["name"],{})
        out.append({
            "endpoint":spec["name"],"method":spec["method"],"path_template":spec["path"],
            "mutation_allowed":False,"payload_present":bool(payload),
            "top_level_contract_passed":isinstance(payload,dict) and any(k in payload for k in spec["roots"]),
        })
    return out

def classify_error(message: str) -> str:
    value=message.lower()
    if "401" in value or "oauth" in value or "token" in value: return "AUTHENTICATION_OR_TOKEN"
    if "403" in value or "permission" in value or "restriction" in value: return "AUTHORIZATION_OR_ACCOUNT_RESTRICTION"
    if "429" in value or "rate" in value: return "RATE_LIMIT"
    if any(x in value for x in ("500","502","503")): return "ETRADE_SERVER_ERROR"
    if any(x in value for x in ("timeout","network","dns")): return "NETWORK_OR_TIMEOUT"
    if any(x in value for x in ("json","schema","mapping")): return "RESPONSE_CONTRACT"
    return "UNKNOWN"
