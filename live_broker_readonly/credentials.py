from __future__ import annotations
import os
from typing import Any

ENVIRONMENT_NAMES = {
    "ALPACA_READ_ONLY": ["ALPACA_API_KEY", "ALPACA_SECRET_KEY"],
    "IBKR_READ_ONLY": ["IBKR_USERNAME", "IBKR_ACCOUNT_ID"],
    "ETRADE_READ_ONLY": [
        "ETRADE_CONSUMER_KEY",
        "ETRADE_CONSUMER_SECRET",
        "ETRADE_ACCESS_TOKEN",
    ],
    "MOCK_READ_ONLY": [],
}

def inspect_credential_presence(adapter_name: str) -> dict[str, Any]:
    names=ENVIRONMENT_NAMES.get(adapter_name,[])
    presence={name:bool(os.environ.get(name)) for name in names}
    return {
        "adapter_name":adapter_name,
        "required_environment_names":names,
        "presence":presence,
        "present_count":sum(1 for value in presence.values() if value),
        "required_count":len(names),
        "complete":all(presence.values()) if names else True,
        "values_exposed":False,
        "credentials_loaded":False,
        "credentials_used":False,
    }
