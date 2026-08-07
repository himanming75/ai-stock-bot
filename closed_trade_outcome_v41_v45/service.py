from __future__ import annotations

import json
import os
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


class ClosedTradeOutcomeCollector:
    """
    READ-ONLY Alpaca Paper outcome collector.

    Allowed broker operations:
      - get_orders()
      - market-data historical bar reads

    No submit/cancel/replace/close methods are present.
    """

    def __init__(self, project_root: Path) -> None:
        self.root = project_root.resolve()
        self.runtime = self.root / "runtime/closed_trade_outcome_v41_v45"
        self.runtime.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _dt(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None

    @staticmethod
    def _write(path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _append(path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, sort_keys=True, default=str) + "\n")

    def _credentials(self) -> tuple[str, str]:
        key = os.getenv("APCA_API_KEY_ID", "").strip()
        secret = os.getenv("APCA_API_SECRET_KEY", "").strip()
        if not key or not secret:
            # Task Scheduler / User environment compatibility.
            try:
                import winreg
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Environment",
                ) as env_key:
                    if not key:
                        key = str(
                            winreg.QueryValueEx(
                                env_key, "APCA_API_KEY_ID"
                            )[0]
                        ).strip()
                    if not secret:
                        secret = str(
                            winreg.QueryValueEx(
                                env_key, "APCA_API_SECRET_KEY"
                            )[0]
                        ).strip()
            except Exception:
                pass
        return key, secret

    def v41_read_paper_filled_orders(self) -> dict[str, Any]:
        key, secret = self._credentials()
        if not key or not secret:
            return {
                "status": "BLOCKED",
                "reason": "PAPER_CREDENTIALS_MISSING",
                "orders": [],
                "order_count": 0,
                "paper_only": True,
                "broker_write_performed": False,
            }

        try:
            from alpaca.trading.client import TradingClient
            from alpaca.trading.enums import QueryOrderStatus
            from alpaca.trading.requests import GetOrdersRequest

            client = TradingClient(key, secret, paper=True)
            orders = client.get_orders(
                filter=GetOrdersRequest(
                    status=QueryOrderStatus.ALL,
                    limit=500,
                )
            )
        except Exception as exc:
            return {
                "status": "BLOCKED",
                "reason": f"ORDER_READ_FAILED:{type(exc).__name__}:{exc}",
                "orders": [],
                "order_count": 0,
                "paper_only": True,
                "broker_write_performed": False,
            }

        rows = []
        for order in orders:
            filled_qty = self._float(getattr(order, "filled_qty", 0))
            filled_price = self._float(
                getattr(order, "filled_avg_price", 0)
            )
            filled_at = getattr(order, "filled_at", None)
            if filled_qty <= 0 or filled_price <= 0 or not filled_at:
                continue

            side_obj = getattr(order, "side", "")
            side = getattr(side_obj, "value", side_obj)
            status_obj = getattr(order, "status", "")
            status = getattr(status_obj, "value", status_obj)

            rows.append({
                "order_id": str(getattr(order, "id", "")),
                "client_order_id": str(
                    getattr(order, "client_order_id", "")
                ),
                "symbol": str(getattr(order, "symbol", "")).upper(),
                "side": str(side).upper(),
                "status": str(status).upper(),
                "filled_qty": filled_qty,
                "filled_avg_price": filled_price,
                "submitted_at": str(
                    getattr(order, "submitted_at", "")
                ),
                "filled_at": str(filled_at),
                "paper": True,
            })

        rows.sort(key=lambda x: x["filled_at"])

        result = {
            "status": "PASS",
            "reason": "READ_ONLY_PAPER_FILLED_ORDERS",
            "orders": rows,
            "order_count": len(rows),
            "paper_only": True,
            "broker_write_performed": False,
        }
        self._write(
            self.runtime / "latest_filled_orders.json",
            result,
        )
        return result

    def v42_build_fifo_round_trips(
        self,
        orders: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Long-side FIFO round-trip builder.
        Existing BUY lots are matched against later SELL fills.
        Unclosed BUY lots remain open and are not fabricated as trades.
        """
        lots: dict[str, deque] = defaultdict(deque)
        trades = []
        seq = 0

        for order in sorted(orders, key=lambda x: x["filled_at"]):
            symbol = order["symbol"]
            side = order["side"]
            qty = self._float(order["filled_qty"])
            price = self._float(order["filled_avg_price"])
            filled_at = order["filled_at"]

            if side == "BUY":
                lots[symbol].append({
                    "qty": qty,
                    "price": price,
                    "time": filled_at,
                    "order_id": order["order_id"],
                })
                continue

            if side != "SELL":
                continue

            remaining = qty
            while remaining > 1e-12 and lots[symbol]:
                lot = lots[symbol][0]
                matched = min(remaining, lot["qty"])
                entry_price = lot["price"]
                exit_price = price
                pnl = (exit_price - entry_price) * matched
                basis = entry_price * matched
                ret = pnl / basis if basis > 0 else 0.0

                seq += 1
                trades.append({
                    "trade_id": (
                        f"{symbol}-{seq:06d}-"
                        f"{lot['order_id'][:8]}-"
                        f"{order['order_id'][:8]}"
                    ),
                    "symbol": symbol,
                    "side": "LONG",
                    "quantity": round(matched, 12),
                    "entry_order_id": lot["order_id"],
                    "exit_order_id": order["order_id"],
                    "entry_time": lot["time"],
                    "exit_time": filled_at,
                    "entry_price": round(entry_price, 8),
                    "exit_price": round(exit_price, 8),
                    "realized_pl": round(pnl, 8),
                    "realized_return": round(ret, 8),
                    "source": "ALPACA_PAPER_FIFO_MATCH",
                })

                lot["qty"] -= matched
                remaining -= matched
                if lot["qty"] <= 1e-12:
                    lots[symbol].popleft()

        open_lots = []
        for symbol, queue in lots.items():
            for lot in queue:
                if lot["qty"] > 1e-12:
                    open_lots.append({
                        "symbol": symbol,
                        "quantity": round(lot["qty"], 12),
                        "entry_price": round(lot["price"], 8),
                        "entry_time": lot["time"],
                        "entry_order_id": lot["order_id"],
                    })

        result = {
            "status": "PASS",
            "closed_trade_count": len(trades),
            "closed_trades": trades,
            "open_lot_count": len(open_lots),
            "open_lots": open_lots,
            "matching_method": "FIFO_LONG_ONLY",
            "broker_write_performed": False,
        }
        self._write(
            self.runtime / "latest_fifo_round_trips.json",
            result,
        )
        return result

    def v43_realized_outcome_ledger(
        self,
        trades: list[dict[str, Any]],
    ) -> dict[str, Any]:
        ledger = self.runtime / "closed_trade_outcomes.jsonl"

        # Rewrite deterministic ledger from current read snapshot to avoid
        # duplicating the same historical trades on every run.
        ledger.parent.mkdir(parents=True, exist_ok=True)
        with ledger.open("w", encoding="utf-8") as f:
            for trade in trades:
                row = {
                    **trade,
                    "outcome_collected_at_utc": self._now(),
                    "paper_only": True,
                    "broker_write_performed": False,
                }
                f.write(json.dumps(row, sort_keys=True) + "\n")

        total_pl = sum(
            self._float(t.get("realized_pl"))
            for t in trades
        )
        wins = sum(
            1 for t in trades
            if self._float(t.get("realized_pl")) > 0
        )
        losses = sum(
            1 for t in trades
            if self._float(t.get("realized_pl")) < 0
        )

        result = {
            "status": "PASS",
            "trade_count": len(trades),
            "wins": wins,
            "losses": losses,
            "win_rate": (
                round(wins / len(trades), 6)
                if trades else None
            ),
            "total_realized_pl": round(total_pl, 8),
            "ledger_path": str(ledger),
            "broker_write_performed": False,
        }
        self._write(
            self.runtime / "latest_realized_outcome_summary.json",
            result,
        )
        return result

    def _fetch_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
    ) -> list[dict[str, Any]]:
        key, secret = self._credentials()
        if not key or not secret:
            return []

        try:
            from alpaca.data.historical import StockHistoricalDataClient
            from alpaca.data.requests import StockBarsRequest
            from alpaca.data.timeframe import TimeFrame

            client = StockHistoricalDataClient(key, secret)
            request = StockBarsRequest(
                symbol_or_symbols=[symbol],
                timeframe=TimeFrame.Minute,
                start=start,
                end=end,
            )
            response = client.get_stock_bars(request)
            bars_obj = response.data.get(symbol, [])
        except Exception:
            return []

        rows = []
        for bar in bars_obj:
            rows.append({
                "timestamp": str(getattr(bar, "timestamp", "")),
                "open": self._float(getattr(bar, "open", 0)),
                "high": self._float(getattr(bar, "high", 0)),
                "low": self._float(getattr(bar, "low", 0)),
                "close": self._float(getattr(bar, "close", 0)),
                "volume": self._float(getattr(bar, "volume", 0)),
            })
        return rows

    def v44_collect_path_metrics(
        self,
        trades: list[dict[str, Any]],
    ) -> dict[str, Any]:
        enriched = []
        available = 0

        for trade in trades:
            entry_dt = self._dt(trade.get("entry_time"))
            exit_dt = self._dt(trade.get("exit_time"))

            row = {
                **trade,
                "mfe": None,
                "mae": None,
                "mfe_pct": None,
                "mae_pct": None,
                "post_exit_1h_return": None,
                "post_exit_4h_return": None,
                "post_exit_close_return": None,
                "path_data_available": False,
            }

            if not entry_dt or not exit_dt:
                enriched.append(row)
                continue

            # Intratrade path + 4h post-exit window.
            bars = self._fetch_bars(
                trade["symbol"],
                entry_dt - timedelta(minutes=1),
                exit_dt + timedelta(hours=4, minutes=5),
            )

            if not bars:
                enriched.append(row)
                continue

            entry_price = self._float(trade["entry_price"])
            exit_price = self._float(trade["exit_price"])

            intratrade = []
            post_exit = []

            for bar in bars:
                ts = self._dt(bar["timestamp"])
                if not ts:
                    continue
                if entry_dt <= ts <= exit_dt:
                    intratrade.append(bar)
                elif ts > exit_dt:
                    post_exit.append((ts, bar))

            if intratrade and entry_price > 0:
                highest = max(b["high"] for b in intratrade)
                lowest = min(b["low"] for b in intratrade)
                mfe = highest - entry_price
                mae = lowest - entry_price

                row["mfe"] = round(mfe, 8)
                row["mae"] = round(mae, 8)
                row["mfe_pct"] = round(mfe / entry_price, 8)
                row["mae_pct"] = round(mae / entry_price, 8)

            if post_exit and exit_price > 0:
                def close_near(target: datetime):
                    candidates = [
                        (abs((ts - target).total_seconds()), bar)
                        for ts, bar in post_exit
                        if ts >= target
                    ]
                    if not candidates:
                        return None
                    _, bar = min(candidates, key=lambda x: x[0])
                    return self._float(bar["close"])

                c1 = close_near(exit_dt + timedelta(hours=1))
                c4 = close_near(exit_dt + timedelta(hours=4))

                if c1:
                    row["post_exit_1h_return"] = round(
                        (c1 - exit_price) / exit_price,
                        8,
                    )
                if c4:
                    row["post_exit_4h_return"] = round(
                        (c4 - exit_price) / exit_price,
                        8,
                    )

                # Best available proxy for "close" in fetched post-exit window.
                last_close = self._float(post_exit[-1][1]["close"])
                if last_close > 0:
                    row["post_exit_close_return"] = round(
                        (last_close - exit_price) / exit_price,
                        8,
                    )

            row["path_data_available"] = any(
                row.get(k) is not None
                for k in [
                    "mfe",
                    "mae",
                    "post_exit_1h_return",
                    "post_exit_4h_return",
                ]
            )
            if row["path_data_available"]:
                available += 1

            enriched.append(row)

        result = {
            "status": (
                "PASS"
                if available > 0
                else "COLLECTING_PATH_DATA"
            ),
            "trade_count": len(trades),
            "path_data_available_count": available,
            "trades": enriched,
            "market_data_read_only": True,
            "fabricated_path_data": False,
            "broker_write_performed": False,
        }
        self._write(
            self.runtime / "latest_enriched_closed_trades.json",
            result,
        )
        return result

    def v45_bridge_v4_v36(
        self,
        enriched: list[dict[str, Any]],
    ) -> dict[str, Any]:
        bridge = self.runtime / "v4_v36_outcome_bridge.json"

        payload = {
            "generated_at_utc": self._now(),
            "source": "ALPACA_PAPER_READ_ONLY",
            "linked_outcomes": enriched,
            "trade_count": len(enriched),
            "paper_only": True,
            "broker_write_performed": False,
            "usage": (
                "Input-compatible bridge for calibration/performance/"
                "trade-audit readers. Existing source files are not overwritten."
            ),
        }
        self._write(bridge, payload)

        # Also expose canonical bridge path for future packages.
        canonical = (
            self.root
            / "runtime/closed_trade_calibration_v4/"
              "external_linked_outcomes_v41_v45.json"
        )
        self._write(canonical, payload)

        return {
            "status": "PASS",
            "bridge_path": str(bridge),
            "canonical_bridge_path": str(canonical),
            "trade_count": len(enriched),
            "existing_v4_file_overwritten": False,
            "existing_v36_file_overwritten": False,
            "broker_write_performed": False,
        }

    def run(self) -> dict[str, Any]:
        v41 = self.v41_read_paper_filled_orders()

        if v41["status"] != "PASS":
            result = {
                "stage": "CLOSED_TRADE_OUTCOME_COLLECTOR_V41_TO_V45",
                "status": "BLOCKED",
                "mode": "READ_ONLY_PAPER_DATA",
                "paper_only": True,
                "etrade_live_write_enabled": False,
                "broker_write_performed": False,
                "v41_paper_order_reader": v41,
                "generated_at_utc": self._now(),
            }
            self._write(
                self.runtime / "latest_closed_trade_outcome_report.json",
                result,
            )
            return result

        v42 = self.v42_build_fifo_round_trips(v41["orders"])
        v43 = self.v43_realized_outcome_ledger(v42["closed_trades"])
        v44 = self.v44_collect_path_metrics(v42["closed_trades"])
        v45 = self.v45_bridge_v4_v36(v44["trades"])

        result = {
            "stage": "CLOSED_TRADE_OUTCOME_COLLECTOR_V41_TO_V45",
            "status": "PASS",
            "mode": "READ_ONLY_PAPER_DATA",
            "paper_only": True,
            "etrade_live_write_enabled": False,
            "broker_write_performed": False,
            "v41_paper_order_reader": v41,
            "v42_fifo_round_trip_builder": v42,
            "v43_realized_outcome_ledger": v43,
            "v44_path_metrics_collector": v44,
            "v45_v4_v36_bridge": v45,
            "generated_at_utc": self._now(),
        }

        self._write(
            self.runtime / "latest_closed_trade_outcome_report.json",
            result,
        )
        self._append(
            self.runtime / "collector_run_ledger.jsonl",
            result,
        )

        summary = {
            "generated_at_utc": self._now(),
            "status": "PASS",
            "filled_order_count": v41["order_count"],
            "closed_trade_count": v42["closed_trade_count"],
            "open_lot_count": v42["open_lot_count"],
            "path_data_available_count": (
                v44["path_data_available_count"]
            ),
            "total_realized_pl": v43["total_realized_pl"],
            "broker_write_performed": False,
            "etrade_live_write_enabled": False,
        }
        self._write(
            self.runtime / "daily_closed_trade_outcome_summary.json",
            summary,
        )

        return result
