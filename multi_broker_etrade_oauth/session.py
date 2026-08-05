from __future__ import annotations
from datetime import datetime, timedelta, timezone

from .models import (
    OAuthAccessToken,
    OAuthSessionState,
    OAuthTemporaryToken,
)
from .storage import JsonTokenStore


class ETradeOAuthSessionManager:
    def __init__(self, store: JsonTokenStore) -> None:
        self.store = store

    def save_request_token(self, token: OAuthTemporaryToken) -> None:
        self.store.save({
            "stage": "REQUEST_TOKEN",
            "request_token": token.to_dict(),
            "verification_code_consumed": False,
            "revoked": False,
        })

    def save_access_token(self, token: OAuthAccessToken) -> None:
        self.store.save({
            "stage": "ACCESS_TOKEN",
            "access_token": {
                "oauth_token": token.oauth_token,
                "oauth_token_secret": token.oauth_token_secret,
                "issued_at_utc": token.issued_at_utc,
                "environment": token.environment,
            },
            "verification_code_consumed": True,
            "revoked": False,
        })

    def mark_revoked(self) -> None:
        payload = self.store.load()
        payload["revoked"] = True
        payload["stage"] = "REVOKED"
        self.store.save(payload)

    def state(
        self,
        *,
        now: datetime | None = None,
        last_activity_utc: datetime | None = None,
    ) -> OAuthSessionState:
        payload = self.store.load()
        now = now or datetime.now(timezone.utc)

        request_present = bool(payload.get("request_token"))
        access_payload = payload.get("access_token") or {}
        access_present = bool(access_payload.get("oauth_token"))
        revoked = bool(payload.get("revoked"))

        renew_required = False
        if access_present and last_activity_utc is not None:
            renew_required = now - last_activity_utc >= timedelta(hours=2)

        reauthorization_required = False
        issued = access_payload.get("issued_at_utc")
        if issued:
            issued_dt = datetime.fromisoformat(issued)
            reauthorization_required = (
                now.astimezone(timezone.utc).date()
                != issued_dt.astimezone(timezone.utc).date()
            )

        status = (
            "REVOKED"
            if revoked
            else "ACCESS_TOKEN_READY"
            if access_present
            else "REQUEST_TOKEN_READY"
            if request_present
            else "NOT_STARTED"
        )

        return OAuthSessionState(
            status=status,
            request_token_present=request_present,
            access_token_present=access_present,
            verification_code_consumed=bool(
                payload.get("verification_code_consumed")
            ),
            renew_required=renew_required,
            reauthorization_required=reauthorization_required,
            revoked=revoked,
        )
