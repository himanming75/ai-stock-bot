from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ETradeTokenState:
    status: str
    last_api_activity_utc: str | None
    eastern_midnight_reauth_required: bool
    inactivity_renewal_required: bool
    renew_endpoint_enabled: bool
    revoke_endpoint_enabled: bool

    def to_dict(self) -> dict:
        return asdict(self)


def initial_token_state() -> ETradeTokenState:
    return ETradeTokenState(
        status="UNKNOWN_UNTIL_EXPLICIT_OAUTH_SESSION",
        last_api_activity_utc=None,
        eastern_midnight_reauth_required=True,
        inactivity_renewal_required=True,
        renew_endpoint_enabled=False,
        revoke_endpoint_enabled=False,
    )
