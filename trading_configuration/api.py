from __future__ import annotations
from pathlib import Path

from .defaults import (
    PROFILES,
    STRATEGIES,
    new_draft,
)
from .storage import (
    load_draft,
    save_draft,
)
from .validation import validate_draft


class TradingConfigurationService:
    def __init__(
        self,
        *,
        draft_path: Path,
        ledger_path: Path,
    ) -> None:
        self.draft_path = draft_path
        self.ledger_path = ledger_path

    def schema(self) -> dict:
        return {
            "profiles": PROFILES,
            "strategy_defaults": STRATEGIES,
            "safety": {
                "draft_only": True,
                "activation_enabled": False,
                "broker_write_enabled": False,
                "order_submission_enabled": False,
                "order_cancel_enabled": False,
            },
        }

    def current(self) -> dict:
        return (
            load_draft(self.draft_path)
            or new_draft()
        )

    def validate(self, payload: dict) -> dict:
        return {
            "status": "VALID",
            "draft": validate_draft(payload),
            "activation_status": "NOT_ACTIVATED",
        }

    def save(self, payload: dict) -> dict:
        draft = validate_draft(payload)
        return save_draft(
            draft=draft,
            draft_path=self.draft_path,
            ledger_path=self.ledger_path,
        )

    def activate(self, payload: dict) -> None:
        raise PermissionError(
            "CONFIGURATION_ACTIVATION_DISABLED"
        )
