from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from smart_safe_guard import SmartSafeTradingGuard


class DailySessionShadowGuard:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()

    @staticmethod
    def _float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _candidate(self) -> dict[str, Any]:
        paths = [
            self.project_root / "release/v14001_15000_paper_autonomous_execution/actual/latest_paper_execution_cycle.json",
            self.project_root / "release/smart_safe_trading_guard_1_0/input/shadow_snapshot.json",
        ]
        for path in paths:
            if not path.exists():
                continue
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
            item = payload.get("selected_candidate") or payload.get("candidate")
            if isinstance(item, dict):
                return {
                    "symbol": str(item.get("symbol", "")).upper(),
                    "side": str(item.get("side", "HOLD")).upper(),
                    "confidence": self._float(item.get("confidence")),
                    "consensus_score": self._float(item.get("consensus_score")),
                    "reward_risk": self._float(item.get("reward_risk")),
                    "quantity": self._float(item.get("quantity")),
                    "reference_price": self._float(item.get("reference_price")),
                }
        return {
            "symbol": "",
            "side": "HOLD",
            "confidence": 0.0,
            "consensus_score": 0.0,
            "reward_risk": 0.0,
            "quantity": 0.0,
            "reference_price": 0.0,
        }

    def _positions(self, client: Any) -> list[dict[str, Any]]:
        result = []
        for position in client.get_all_positions():
            result.append({
                "symbol": str(getattr(position, "symbol", "")),
                "market_value": self._float(getattr(position, "market_value", 0)),
                "qty": self._float(getattr(position, "qty", 0)),
                "unrealized_pl": self._float(getattr(position, "unrealized_pl", 0)),
            })
        return result

    def evaluate(
        self,
        *,
        client: Any,
        account: Any,
        clock: dict[str, Any],
        today_order_count: int,
    ) -> dict[str, Any]:
        candidate = self._candidate()

        # Recover a usable reference price from the most recent Alpaca
        # Paper order for the selected symbol when the AI candidate
        # snapshot does not contain quantity or price.
        if (
            candidate["symbol"]
            and (
                candidate["reference_price"] <= 0
                or candidate["quantity"] <= 0
            )
        ):
            try:
                from alpaca.trading.enums import QueryOrderStatus
                from alpaca.trading.requests import GetOrdersRequest

                recent_orders = client.get_orders(
                    filter=GetOrdersRequest(
                        status=QueryOrderStatus.ALL,
                        limit=100,
                    )
                )

                for order in recent_orders:
                    if (
                        str(getattr(order, "symbol", "")).upper()
                        != candidate["symbol"]
                    ):
                        continue

                    recovered_price = self._float(
                        getattr(order, "filled_avg_price", 0)
                    )

                    if recovered_price <= 0:
                        recovered_price = self._float(
                            getattr(order, "limit_price", 0)
                        )

                    if recovered_price > 0:
                        candidate["reference_price"] = recovered_price
                        break
            except Exception:
                pass

        if (
            candidate["quantity"] <= 0
            and candidate["reference_price"] > 0
        ):
            candidate["quantity"] = round(
                min(100.0 / candidate["reference_price"], 1.0),
                9,
            )

        equity = self._float(getattr(account, "equity", 0))
        last_equity = self._float(getattr(account, "last_equity", equity))

        result = SmartSafeTradingGuard(self.project_root).evaluate(
            policy_path=self.project_root / "release/smart_safe_trading_guard_1_0/config/guard_policy.json",
            candidate=candidate,
            account={
                "status": (
                    getattr(
                        getattr(account, "status", ""),
                        "value",
                        getattr(account, "status", ""),
                    )
                    or ""
                ),
                "trading_blocked": bool(
                    getattr(account, "trading_blocked", False)
                ),
                "buying_power": self._float(
                    getattr(account, "buying_power", 0)
                ),
            },
            risk={
                "daily_orders": int(today_order_count),
                "daily_pnl": round(equity - last_equity, 6),
                "consecutive_losses": 0,
                "emergency_stop_engaged": False,
            },
            market={
                "market_open": bool(clock.get("market_open", False)),
                "minutes_to_close": int(clock.get("minutes_to_close", 0)),
                "volatility_risk": 0.5,
                "market_regime_fit": 0.5,
            },
            positions=self._positions(client),
            decision_path=self.project_root / "runtime/paper_autonomous_daily_session/latest_shadow_guard_decision.json",
            ledger_path=self.project_root / "runtime/paper_autonomous_daily_session/shadow_guard_ledger.jsonl",
        )
        return {
            "observed_at_utc": datetime.now(timezone.utc).isoformat(),
            "mode": "SHADOW",
            "enforced": False,
            "action": result.get("action"),
            "would_allow_order": result.get("would_allow_order", False),
            "quality_score": result.get("quality_score"),
            "issue_codes": [x.get("code") for x in result.get("issues", [])],
        }
