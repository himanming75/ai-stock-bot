from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )


def append_jsonl(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str) + "\n")


@dataclass(frozen=True)
class PaperLifecycleConfig:
    take_profit_pct: float = 0.008
    stop_loss_pct: float = 0.005
    max_hold_minutes: int = 30
    force_flat_before_close: bool = True
    fill_wait_seconds: int = 20
    fill_poll_seconds: int = 2

    @classmethod
    def load(cls, path: Path) -> "PaperLifecycleConfig":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return cls(
            take_profit_pct=float(data.get("take_profit_pct", 0.008)),
            stop_loss_pct=float(data.get("stop_loss_pct", 0.005)),
            max_hold_minutes=int(data.get("max_hold_minutes", 30)),
            force_flat_before_close=bool(data.get("force_flat_before_close", True)),
            fill_wait_seconds=int(data.get("fill_wait_seconds", 20)),
            fill_poll_seconds=int(data.get("fill_poll_seconds", 2)),
        )


class PaperPositionLifecycle:
    def __init__(self, project_root: Path) -> None:
        self.root = project_root.resolve()
        self.runtime = self.root / "runtime/paper_full_auto_lifecycle"
        self.runtime.mkdir(parents=True, exist_ok=True)
        self.config = PaperLifecycleConfig.load(
            self.root / "config/paper_full_auto_lifecycle.json"
        )
        self.registry_path = self.runtime / "position_registry.json"
        self.exit_ledger_path = self.runtime / "exit_ledger.jsonl"
        self.closed_ledger_path = self.runtime / "closed_round_trips.jsonl"
        self.latest_path = self.runtime / "latest_lifecycle_status.json"

    def _registry(self) -> dict[str, Any]:
        return read_json(self.registry_path).get("positions", {}) or {}

    def _save_registry(self, rows: dict[str, Any]) -> None:
        write_json(
            self.registry_path,
            {
                "paper_only": True,
                "updated_at_utc": utc_now(),
                "positions": rows,
            },
        )

    def _hold_minutes(self, opened_at: str) -> float:
        try:
            opened = datetime.fromisoformat(str(opened_at).replace("Z", "+00:00"))
            if opened.tzinfo is None:
                opened = opened.replace(tzinfo=timezone.utc)
            return max(
                0.0,
                (datetime.now(timezone.utc) - opened.astimezone(timezone.utc)).total_seconds() / 60.0,
            )
        except Exception:
            return 0.0

    def sync_positions(self, client):
        positions = list(client.get_all_positions())
        registry = self._registry()
        now = utc_now()

        for position in positions:
            symbol = str(getattr(position, "symbol", "")).upper()
            if not symbol:
                continue

            row = registry.get(symbol, {})
            if not row:
                row = {
                    "symbol": symbol,
                    "opened_at_utc": now,
                    "entry_time_inferred": True,
                    "paper_only": True,
                }

            row.update(
                {
                    "last_seen_at_utc": now,
                    "qty": as_float(getattr(position, "qty", 0)),
                    "avg_entry_price": as_float(getattr(position, "avg_entry_price", 0)),
                    "current_price": as_float(getattr(position, "current_price", 0)),
                    "market_value": as_float(getattr(position, "market_value", 0)),
                    "unrealized_pl": as_float(getattr(position, "unrealized_pl", 0)),
                    "unrealized_plpc": as_float(getattr(position, "unrealized_plpc", 0)),
                }
            )
            registry[symbol] = row

        self._save_registry(registry)
        return positions, registry

    def _exit_reason(self, row: dict[str, Any], minutes_to_close: int) -> str | None:
        entry = as_float(row.get("avg_entry_price"))
        current = as_float(row.get("current_price"))
        if entry <= 0 or current <= 0:
            return None

        ret = (current - entry) / entry
        if ret >= self.config.take_profit_pct:
            return "TAKE_PROFIT"
        if ret <= -self.config.stop_loss_pct:
            return "STOP_LOSS"
        if self._hold_minutes(str(row.get("opened_at_utc", ""))) >= self.config.max_hold_minutes:
            return "TIME_EXIT"
        if self.config.force_flat_before_close and minutes_to_close <= 15:
            return "MARKET_CLOSE_FLATTEN"
        return None

    def _get_order(self, client, order_id: str):
        try:
            return client.get_order_by_id(order_id)
        except TypeError:
            return client.get_order_by_id(order_id=order_id)

    def _wait_for_fill(self, client, order_id: str):
        deadline = time.time() + max(1, self.config.fill_wait_seconds)
        last = None
        while time.time() <= deadline:
            try:
                last = self._get_order(client, order_id)
            except Exception:
                time.sleep(max(1, self.config.fill_poll_seconds))
                continue

            status = str(getattr(last, "status", "")).lower()
            if "filled" in status:
                return last
            if any(x in status for x in ("canceled", "rejected", "expired")):
                return last
            time.sleep(max(1, self.config.fill_poll_seconds))
        return last

    def _submit_exit(self, client, symbol: str, qty: float, reason: str) -> dict[str, Any]:
        from alpaca.trading.enums import OrderSide, TimeInForce
        from alpaca.trading.requests import MarketOrderRequest

        if qty <= 0:
            return {
                "status": "BLOCKED",
                "reason": "ZERO_EXIT_QTY",
                "symbol": symbol,
                "paper_only": True,
            }

        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        client_order_id = f"paper-exit-{symbol.lower()}-{stamp}"[:48]

        request = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
            client_order_id=client_order_id,
        )
        order = client.submit_order(order_data=request)

        result = {
            "status": "PAPER_EXIT_SUBMITTED",
            "symbol": symbol,
            "qty": qty,
            "reason": reason,
            "paper_only": True,
            "live_order_submitted": False,
            "order_id": str(getattr(order, "id", "")),
            "client_order_id": client_order_id,
            "submitted_at_utc": utc_now(),
        }
        append_jsonl(self.exit_ledger_path, result)
        return result

    def evaluate_and_exit(self, client, *, minutes_to_close: int) -> dict[str, Any]:
        positions, registry = self.sync_positions(client)
        actions: list[dict[str, Any]] = []

        for position in positions:
            symbol = str(getattr(position, "symbol", "")).upper()
            if not symbol:
                continue

            row = registry.get(symbol, {})
            pending = str(row.get("exit_pending_order_id", "") or "")

            if pending:
                try:
                    existing = self._get_order(client, pending)
                    status = str(getattr(existing, "status", "")).lower()
                    if "filled" not in status and not any(
                        x in status for x in ("canceled", "rejected", "expired")
                    ):
                        actions.append(
                            {
                                "symbol": symbol,
                                "action": "WAIT_PENDING_EXIT",
                                "order_id": pending,
                                "status": status,
                            }
                        )
                        continue
                    row.pop("exit_pending_order_id", None)
                    registry[symbol] = row
                except Exception:
                    actions.append(
                        {
                            "symbol": symbol,
                            "action": "WAIT_PENDING_EXIT_LOOKUP_ERROR",
                            "order_id": pending,
                        }
                    )
                    continue

            reason = self._exit_reason(row, minutes_to_close)
            if not reason:
                continue

            qty = as_float(
                getattr(position, "qty_available", None),
                as_float(getattr(position, "qty", 0)),
            )
            if qty <= 0:
                qty = as_float(getattr(position, "qty", 0))

            submitted = self._submit_exit(client, symbol, qty, reason)
            order_id = submitted.get("order_id", "")
            if not order_id:
                actions.append(submitted)
                continue

            row["exit_pending_order_id"] = order_id
            row["exit_reason"] = reason
            registry[symbol] = row
            self._save_registry(registry)

            filled = self._wait_for_fill(client, order_id)
            filled_status = str(getattr(filled, "status", "")).lower() if filled else ""
            filled_qty = as_float(getattr(filled, "filled_qty", qty)) if filled else 0.0
            exit_price = as_float(getattr(filled, "filled_avg_price", 0)) if filled else 0.0

            if filled and "filled" in filled_status and filled_qty > 0 and exit_price > 0:
                entry_price = as_float(row.get("avg_entry_price"))
                realized_pl = (exit_price - entry_price) * filled_qty
                realized_return = (
                    (exit_price - entry_price) / entry_price
                    if entry_price > 0
                    else None
                )
                trade = {
                    "trade_id": f"paper-roundtrip-{symbol.lower()}-{order_id}",
                    "symbol": symbol,
                    "side": "LONG",
                    "entry_price": entry_price,
                    "entry_time": row.get("opened_at_utc"),
                    "entry_time_inferred": True,
                    "exit_price": exit_price,
                    "exit_time": utc_now(),
                    "quantity": filled_qty,
                    "realized_pl": round(realized_pl, 8),
                    "realized_return": (
                        round(realized_return, 8)
                        if realized_return is not None
                        else None
                    ),
                    "hold_minutes": round(self._hold_minutes(str(row.get("opened_at_utc", ""))), 4),
                    "exit_reason": reason,
                    "exit_order_id": order_id,
                    "paper_only": True,
                    "live_order_submitted": False,
                }
                append_jsonl(self.closed_ledger_path, trade)
                registry.pop(symbol, None)
                self._save_registry(registry)
                actions.append({"symbol": symbol, "action": "CLOSED", "trade": trade})
            else:
                actions.append(
                    {
                        "symbol": symbol,
                        "action": "EXIT_SUBMITTED_NOT_FILLED_YET",
                        "order_id": order_id,
                        "status": filled_status,
                        "reason": reason,
                    }
                )

        result = {
            "status": "PASS",
            "paper_only": True,
            "live_order_submitted": False,
            "actions": actions,
            "action_count": len(actions),
            "updated_at_utc": utc_now(),
        }
        write_json(self.latest_path, result)
        return result