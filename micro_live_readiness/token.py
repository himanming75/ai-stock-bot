from __future__ import annotations
from typing import Any

def inspect_token(policy:dict[str,Any])->dict[str,Any]:
    return {
        "token_present":False,
        "token_valid":False,
        "token_used":False,
        "token_single_use":True,
        "token_expired":False,
        "token_replay_detected":False,
        "token_issued_for_live":False,
    }
