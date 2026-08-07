from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json


@dataclass(frozen=True)
class PaperExecutionProfile:
    profile_name: str
    paper_submission_enabled: bool
    live_submission_enabled: bool
    max_orders_per_session: int
    max_notional_per_order: float
    allowed_symbols: tuple[str, ...]
    min_confidence: float
    min_reward_risk: float
    poll_seconds: int
    require_market_open: bool
    require_manual_arm_token: bool

    @classmethod
    def load(cls, path: Path) -> "PaperExecutionProfile":
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return cls(
            profile_name=str(data["profile_name"]),
            paper_submission_enabled=bool(data["paper_submission_enabled"]),
            live_submission_enabled=bool(data["live_submission_enabled"]),
            max_orders_per_session=int(data["max_orders_per_session"]),
            max_notional_per_order=float(data["max_notional_per_order"]),
            allowed_symbols=tuple(data["allowed_symbols"]),
            min_confidence=float(data["min_confidence"]),
            min_reward_risk=float(data["min_reward_risk"]),
            poll_seconds=int(data["poll_seconds"]),
            require_market_open=bool(data["require_market_open"]),
            require_manual_arm_token=bool(data["require_manual_arm_token"]),
        )

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.live_submission_enabled:
            errors.append("LIVE_SUBMISSION_MUST_REMAIN_OFF")
        if self.max_orders_per_session < 1:
            errors.append("MAX_ORDERS_PER_SESSION_INVALID")
        if not (0 < self.max_notional_per_order <= 1000):
            errors.append("MAX_NOTIONAL_PER_ORDER_INVALID")
        if not self.allowed_symbols:
            errors.append("ALLOWED_SYMBOLS_EMPTY")
        if not (0 <= self.min_confidence <= 1):
            errors.append("MIN_CONFIDENCE_INVALID")
        if self.min_reward_risk < 0:
            errors.append("MIN_REWARD_RISK_INVALID")
        if self.poll_seconds < 15:
            errors.append("POLL_SECONDS_TOO_LOW")
        return errors
