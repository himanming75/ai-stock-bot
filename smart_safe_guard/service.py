from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GuardPolicy:
    mode: str = "SHADOW"
    minimum_confidence: float = 0.80
    minimum_consensus_score: float = 0.75
    minimum_reward_risk: float = 1.50
    maximum_order_notional: float = 100.0
    maximum_daily_orders: int = 1
    maximum_open_positions: int = 2
    maximum_daily_loss: float = 50.0
    maximum_consecutive_losses: int = 2
    maximum_symbol_exposure: float = 500.0
    minimum_minutes_to_close: int = 15
    block_duplicate_symbol_buy: bool = True
    live_write_enabled: bool = False

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "GuardPolicy":
        return cls(**{key: payload[key] for key in asdict(cls()).keys()
                      if key in payload})


class SmartSafeTradingGuard:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _write(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _append(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")

    @staticmethod
    def _score(
        confidence: float,
        consensus_score: float,
        reward_risk: float,
        volatility_risk: float,
        market_regime_fit: float,
    ) -> float:
        rr_normalized = min(max(reward_risk / 3.0, 0.0), 1.0)
        volatility_quality = 1.0 - min(max(volatility_risk, 0.0), 1.0)
        score = (
            0.30 * confidence
            + 0.25 * consensus_score
            + 0.20 * rr_normalized
            + 0.15 * market_regime_fit
            + 0.10 * volatility_quality
        )
        return round(min(max(score, 0.0), 1.0), 6)

    def evaluate(
        self,
        *,
        policy_path: Path,
        candidate: dict[str, Any],
        account: dict[str, Any],
        risk: dict[str, Any],
        market: dict[str, Any],
        positions: list[dict[str, Any]],
        decision_path: Path,
        ledger_path: Path,
    ) -> dict[str, Any]:
        policy_payload = json.loads(policy_path.read_text(encoding="utf-8-sig"))
        policy = GuardPolicy.from_mapping(policy_payload)

        issues: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []

        if policy.mode not in {"SHADOW", "ENFORCE"}:
            issues.append({"code": "INVALID_MODE", "blocking": True})

        if policy.live_write_enabled:
            issues.append({"code": "LIVE_WRITE_MUST_REMAIN_OFF", "blocking": True})

        symbol = str(candidate.get("symbol", "")).strip().upper()
        side = str(candidate.get("side", "")).strip().upper()
        confidence = float(candidate.get("confidence", 0.0))
        consensus = float(candidate.get("consensus_score", 0.0))
        reward_risk = float(candidate.get("reward_risk", 0.0))
        quantity = float(candidate.get("quantity", 0.0))
        reference_price = float(candidate.get("reference_price", 0.0))
        estimated_notional = quantity * reference_price

        daily_orders = int(risk.get("daily_orders", 0))
        daily_pnl = float(risk.get("daily_pnl", 0.0))
        consecutive_losses = int(risk.get("consecutive_losses", 0))
        emergency_stop = bool(risk.get("emergency_stop_engaged", False))

        market_open = bool(market.get("market_open", False))
        minutes_to_close = int(market.get("minutes_to_close", 0))
        volatility_risk = float(market.get("volatility_risk", 0.5))
        market_regime_fit = float(market.get("market_regime_fit", 0.5))

        account_status = str(account.get("status", "")).upper()
        trading_blocked = bool(account.get("trading_blocked", False))
        buying_power = float(account.get("buying_power", 0.0))

        same_symbol_positions = [
            position for position in positions
            if str(position.get("symbol", "")).upper() == symbol
        ]
        symbol_exposure = sum(
            abs(float(position.get("market_value", 0.0)))
            for position in same_symbol_positions
        )

        if not symbol:
            issues.append({"code": "SYMBOL_MISSING", "blocking": True})
        if side not in {"BUY", "SELL", "HOLD"}:
            issues.append({"code": "INVALID_SIDE", "blocking": True})
        if side in {"BUY", "SELL"} and quantity <= 0:
            issues.append({"code": "ZERO_QUANTITY", "blocking": True})
        if confidence < policy.minimum_confidence:
            issues.append({"code": "CONFIDENCE_TOO_LOW", "blocking": True})
        if consensus < policy.minimum_consensus_score:
            issues.append({"code": "CONSENSUS_TOO_LOW", "blocking": True})
        if reward_risk < policy.minimum_reward_risk:
            issues.append({"code": "REWARD_RISK_TOO_LOW", "blocking": True})
        if estimated_notional > policy.maximum_order_notional:
            issues.append({"code": "ORDER_NOTIONAL_LIMIT", "blocking": True})
        if daily_orders >= policy.maximum_daily_orders:
            issues.append({"code": "DAILY_ORDER_LIMIT", "blocking": True})
        if len(positions) >= policy.maximum_open_positions and side == "BUY":
            issues.append({"code": "OPEN_POSITION_LIMIT", "blocking": True})
        if daily_pnl <= -policy.maximum_daily_loss:
            issues.append({"code": "DAILY_LOSS_LIMIT", "blocking": True})
        if consecutive_losses >= policy.maximum_consecutive_losses:
            issues.append({"code": "CONSECUTIVE_LOSS_LIMIT", "blocking": True})
        if symbol_exposure + estimated_notional > policy.maximum_symbol_exposure:
            issues.append({"code": "SYMBOL_EXPOSURE_LIMIT", "blocking": True})
        if policy.block_duplicate_symbol_buy and same_symbol_positions and side == "BUY":
            issues.append({"code": "DUPLICATE_SYMBOL_BUY", "blocking": True})
        if not market_open:
            issues.append({"code": "MARKET_CLOSED", "blocking": True})
        if minutes_to_close <= policy.minimum_minutes_to_close:
            issues.append({"code": "MARKET_CLOSE_BUFFER", "blocking": True})
        if account_status != "ACTIVE":
            issues.append({"code": "ACCOUNT_NOT_ACTIVE", "blocking": True})
        if trading_blocked:
            issues.append({"code": "ACCOUNT_TRADING_BLOCKED", "blocking": True})
        if buying_power < estimated_notional:
            issues.append({"code": "INSUFFICIENT_BUYING_POWER", "blocking": True})
        if emergency_stop:
            issues.append({"code": "EMERGENCY_STOP", "blocking": True})

        if volatility_risk >= 0.80:
            warnings.append({"code": "HIGH_VOLATILITY"})
        if market_regime_fit < 0.60:
            warnings.append({"code": "WEAK_MARKET_REGIME_FIT"})

        quality_score = self._score(
            confidence,
            consensus,
            reward_risk,
            volatility_risk,
            market_regime_fit,
        )

        blocking = [item for item in issues if item.get("blocking")]
        would_allow = not blocking and side in {"BUY", "SELL"}

        if policy.mode == "SHADOW":
            action = "SHADOW_ALLOW" if would_allow else "SHADOW_BLOCK"
            enforced = False
        else:
            action = "ALLOW" if would_allow else "BLOCK"
            enforced = True

        result = {
            "stage": "SMART_SAFE_TRADING_GUARD_1_0",
            "status": "PASS",
            "mode": policy.mode,
            "enforced": enforced,
            "action": action,
            "would_allow_order": would_allow,
            "paper_only": True,
            "etrade_live_write_enabled": False,
            "live_orders_submitted": 0,
            "candidate": {
                "symbol": symbol,
                "side": side,
                "confidence": confidence,
                "consensus_score": consensus,
                "reward_risk": reward_risk,
                "quantity": quantity,
                "reference_price": reference_price,
                "estimated_notional": round(estimated_notional, 6),
            },
            "quality_score": quality_score,
            "account_ready": (
                account_status == "ACTIVE"
                and not trading_blocked
                and buying_power >= estimated_notional
            ),
            "risk_snapshot": {
                "daily_orders": daily_orders,
                "daily_pnl": daily_pnl,
                "consecutive_losses": consecutive_losses,
                "open_positions": len(positions),
                "symbol_exposure": round(symbol_exposure, 6),
            },
            "market_snapshot": {
                "market_open": market_open,
                "minutes_to_close": minutes_to_close,
                "volatility_risk": volatility_risk,
                "market_regime_fit": market_regime_fit,
            },
            "issues": issues,
            "warnings": warnings,
            "blocking_issue_count": len(blocking),
            "policy": asdict(policy),
            "observed_at_utc": self._utc_now(),
        }
        self._write(decision_path, result)
        self._append(ledger_path, result)
        return result
