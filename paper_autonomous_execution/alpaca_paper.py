from __future__ import annotations
import os
from typing import Any


class AlpacaPaperAdapter:
    def __init__(self) -> None:
        self.api_key = os.getenv("APCA_API_KEY_ID", "").strip()
        self.api_secret = os.getenv("APCA_API_SECRET_KEY", "").strip()

    def credentials_present(self) -> bool:
        return bool(self.api_key and self.api_secret)

    def _client(self):
        try:
            from alpaca.trading.client import TradingClient
        except ImportError as exc:
            raise RuntimeError("ALPACA_PY_NOT_INSTALLED") from exc
        return TradingClient(self.api_key, self.api_secret, paper=True)

    def preflight(self) -> dict[str, Any]:
        if not self.credentials_present():
            return {
                "status": "BLOCKED",
                "reason": "PAPER_CREDENTIALS_MISSING",
                "paper": True,
            }
        try:
            client = self._client()
            account = client.get_account()
            clock = client.get_clock()
        except Exception as exc:
            return {
                "status": "BLOCKED",
                "reason": f"ALPACA_PREFLIGHT_ERROR:{type(exc).__name__}",
                "paper": True,
            }
        return {
            "status": "PASS",
            "paper": True,
            "account_status": str(getattr(account, "status", "")),
            "trading_blocked": bool(
                getattr(account, "trading_blocked", True)
            ),
            "account_blocked": bool(
                getattr(account, "account_blocked", True)
            ),
            "market_open": bool(getattr(clock, "is_open", False)),
            "next_open": str(getattr(clock, "next_open", "")),
            "next_close": str(getattr(clock, "next_close", "")),
        }

    def open_position_symbols(self) -> set[str]:
        client = self._client()
        return {
            str(getattr(position, "symbol", "")).upper()
            for position in client.get_all_positions()
            if str(getattr(position, "symbol", "")).strip()
        }

    def submit_market_notional(
        self,
        *,
        symbol: str,
        side: str,
        notional: float,
        client_order_id: str,
    ) -> dict[str, Any]:
        from alpaca.trading.enums import OrderSide, TimeInForce
        from alpaca.trading.requests import MarketOrderRequest

        client = self._client()
        request = MarketOrderRequest(
            symbol=symbol,
            notional=round(notional, 2),
            side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
            client_order_id=client_order_id,
        )
        order = client.submit_order(order_data=request)
        return {
            "id": str(getattr(order, "id", "")),
            "client_order_id": str(
                getattr(order, "client_order_id", client_order_id)
            ),
            "symbol": str(getattr(order, "symbol", symbol)),
            "side": str(getattr(order, "side", side)),
            "status": str(getattr(order, "status", "")),
            "paper": True,
        }
