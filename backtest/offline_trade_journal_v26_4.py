from __future__ import annotations

"""
V26.4 Offline Trade Journal Engine

Features:
- deterministic trade ID generation
- entry/exit records
- LONG/SHORT support
- signal/indicator/portfolio snapshots
- commission, slippage, holding period, gross/net P&L
- tags
- JSON persistence
- CSV export
- SHA-256 integrity verification
- duplicate ID and tamper detection

Safety boundary:
- no network access
- no account/broker APIs
- no live order creation/submission
- no live execution
"""

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Mapping
import csv
import json

VERSION = "26.4"
ZERO = Decimal("0")
CENT = Decimal("0.01")
QTY_STEP = Decimal("0.000001")


class JournalError(ValueError):
    pass


def _d(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise JournalError(f"invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise JournalError("decimal value must be finite")
    return result


def _money(value: Any) -> Decimal:
    return _d(value).quantize(CENT, rounding=ROUND_HALF_UP)


def _qty(value: Any) -> Decimal:
    return _d(value).quantize(QTY_STEP, rounding=ROUND_HALF_UP)


def _symbol(value: str) -> str:
    result = value.strip().upper()
    if not result or len(result) > 15 or not all(c.isalnum() or c in ".-" for c in result):
        raise JournalError("invalid symbol")
    return result


def _timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise JournalError("timestamp must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise JournalError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc).isoformat()


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


def _normalize_snapshot(value: Mapping[str, Any] | None) -> tuple[tuple[str, str], ...]:
    if value is None:
        return ()
    normalized = []
    for key, item in value.items():
        name = str(key).strip()
        if not name:
            raise JournalError("snapshot keys cannot be empty")
        normalized.append((name, str(item)))
    return tuple(sorted(normalized))


def _snapshot_dict(value: tuple[tuple[str, str], ...]) -> dict[str, str]:
    return dict(value)


@dataclass(frozen=True)
class TradeEntry:
    trade_id: str
    symbol: str
    direction: str
    entry_time: str
    entry_price: Decimal
    quantity: Decimal
    signal_reason: str
    signal_snapshot: tuple[tuple[str, str], ...]
    indicator_snapshot: tuple[tuple[str, str], ...]
    portfolio_snapshot: tuple[tuple[str, str], ...]
    entry_commission: Decimal
    entry_slippage: Decimal
    tags: tuple[str, ...]


@dataclass(frozen=True)
class TradeRecord:
    version: str
    entry: TradeEntry
    exit_time: str | None
    exit_price: Decimal | None
    exit_reason: str | None
    exit_commission: Decimal
    exit_slippage: Decimal
    gross_pnl: Decimal
    net_pnl: Decimal
    holding_seconds: int
    record_hash: str


@dataclass(frozen=True)
class TradeJournal:
    version: str
    trades: tuple[TradeRecord, ...]
    journal_hash: str


def _entry_payload(entry: TradeEntry) -> dict[str, Any]:
    return {
        "trade_id": entry.trade_id,
        "symbol": entry.symbol,
        "direction": entry.direction,
        "entry_time": entry.entry_time,
        "entry_price": str(entry.entry_price),
        "quantity": str(entry.quantity),
        "signal_reason": entry.signal_reason,
        "signal_snapshot": _snapshot_dict(entry.signal_snapshot),
        "indicator_snapshot": _snapshot_dict(entry.indicator_snapshot),
        "portfolio_snapshot": _snapshot_dict(entry.portfolio_snapshot),
        "entry_commission": str(entry.entry_commission),
        "entry_slippage": str(entry.entry_slippage),
        "tags": list(entry.tags),
    }


def _record_payload(record: TradeRecord, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": record.version,
        "entry": _entry_payload(record.entry),
        "exit_time": record.exit_time,
        "exit_price": None if record.exit_price is None else str(record.exit_price),
        "exit_reason": record.exit_reason,
        "exit_commission": str(record.exit_commission),
        "exit_slippage": str(record.exit_slippage),
        "gross_pnl": str(record.gross_pnl),
        "net_pnl": str(record.net_pnl),
        "holding_seconds": record.holding_seconds,
    }
    if include_hash:
        payload["record_hash"] = record.record_hash
    return payload


def _journal_payload(journal: TradeJournal, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": journal.version,
        "trades": [_record_payload(trade, include_hash=True) for trade in journal.trades],
    }
    if include_hash:
        payload["journal_hash"] = journal.journal_hash
    return payload


def _trade_id(
    symbol: str,
    direction: str,
    entry_time: str,
    entry_price: Decimal,
    quantity: Decimal,
) -> str:
    digest = _hash({
        "symbol": symbol,
        "direction": direction,
        "entry_time": entry_time,
        "entry_price": str(entry_price),
        "quantity": str(quantity),
    })
    return f"TRD-{digest[:16].upper()}"


def create_trade(
    symbol: str,
    direction: str,
    entry_time: str,
    entry_price: Any,
    quantity: Any,
    *,
    signal_reason: str,
    signal_snapshot: Mapping[str, Any] | None = None,
    indicator_snapshot: Mapping[str, Any] | None = None,
    portfolio_snapshot: Mapping[str, Any] | None = None,
    entry_commission: Any = 0,
    entry_slippage: Any = 0,
    tags: Iterable[str] = (),
) -> TradeRecord:
    sym = _symbol(symbol)
    direction_n = direction.strip().upper()
    if direction_n not in {"LONG", "SHORT"}:
        raise JournalError("direction must be LONG or SHORT")
    time_n = _timestamp(entry_time)
    price = _money(entry_price)
    qty = _qty(quantity)
    commission = _money(entry_commission)
    slippage = _money(entry_slippage)
    if price <= ZERO or qty <= ZERO:
        raise JournalError("entry price and quantity must be positive")
    if commission < ZERO or slippage < ZERO:
        raise JournalError("entry costs cannot be negative")
    reason = signal_reason.strip()
    if not reason:
        raise JournalError("signal_reason is required")
    normalized_tags = tuple(sorted({str(tag).strip() for tag in tags if str(tag).strip()}))

    entry = TradeEntry(
        trade_id=_trade_id(sym, direction_n, time_n, price, qty),
        symbol=sym,
        direction=direction_n,
        entry_time=time_n,
        entry_price=price,
        quantity=qty,
        signal_reason=reason,
        signal_snapshot=_normalize_snapshot(signal_snapshot),
        indicator_snapshot=_normalize_snapshot(indicator_snapshot),
        portfolio_snapshot=_normalize_snapshot(portfolio_snapshot),
        entry_commission=commission,
        entry_slippage=slippage,
        tags=normalized_tags,
    )
    record = TradeRecord(
        version=VERSION,
        entry=entry,
        exit_time=None,
        exit_price=None,
        exit_reason=None,
        exit_commission=ZERO,
        exit_slippage=ZERO,
        gross_pnl=ZERO,
        net_pnl=ZERO,
        holding_seconds=0,
        record_hash="",
    )
    return replace(record, record_hash=_hash(_record_payload(record)))


def close_trade(
    record: TradeRecord,
    exit_time: str,
    exit_price: Any,
    *,
    exit_reason: str,
    exit_commission: Any = 0,
    exit_slippage: Any = 0,
) -> TradeRecord:
    verify_record(record)
    if record.exit_time is not None:
        raise JournalError("trade is already closed")

    time_n = _timestamp(exit_time)
    if time_n <= record.entry.entry_time:
        raise JournalError("exit time must be after entry time")

    price = _money(exit_price)
    commission = _money(exit_commission)
    slippage = _money(exit_slippage)
    if price <= ZERO:
        raise JournalError("exit price must be positive")
    if commission < ZERO or slippage < ZERO:
        raise JournalError("exit costs cannot be negative")
    reason = exit_reason.strip()
    if not reason:
        raise JournalError("exit_reason is required")

    direction = Decimal("1") if record.entry.direction == "LONG" else Decimal("-1")
    gross = _money(
        (price - record.entry.entry_price)
        * record.entry.quantity
        * direction
    )
    net = _money(
        gross
        - record.entry.entry_commission
        - commission
        - record.entry.entry_slippage
        - slippage
    )
    start = datetime.fromisoformat(record.entry.entry_time)
    end = datetime.fromisoformat(time_n)
    holding_seconds = int((end - start).total_seconds())

    closed = replace(
        record,
        exit_time=time_n,
        exit_price=price,
        exit_reason=reason,
        exit_commission=commission,
        exit_slippage=slippage,
        gross_pnl=gross,
        net_pnl=net,
        holding_seconds=holding_seconds,
        record_hash="",
    )
    return replace(closed, record_hash=_hash(_record_payload(closed)))


def verify_record(record: TradeRecord) -> bool:
    if record.version != VERSION:
        raise JournalError("unsupported trade record version")
    if record.entry.entry_price <= ZERO or record.entry.quantity <= ZERO:
        raise JournalError("invalid entry values")
    if record.entry.direction not in {"LONG", "SHORT"}:
        raise JournalError("invalid direction")
    if record.exit_time is None:
        if any((
            record.exit_price is not None,
            record.exit_reason is not None,
            record.holding_seconds != 0,
            record.gross_pnl != ZERO,
            record.net_pnl != ZERO,
        )):
            raise JournalError("open trade contains exit data")
    else:
        if record.exit_price is None or record.exit_reason is None:
            raise JournalError("closed trade is missing exit data")
        if record.holding_seconds <= 0:
            raise JournalError("closed trade must have positive holding time")
    clean = replace(record, record_hash="")
    if record.record_hash != _hash(_record_payload(clean)):
        raise JournalError("trade record hash mismatch")
    return True


def create_journal(records: Iterable[TradeRecord]) -> TradeJournal:
    trades = tuple(sorted(records, key=lambda item: item.entry.trade_id))
    if len({item.entry.trade_id for item in trades}) != len(trades):
        raise JournalError("duplicate trade IDs detected")
    for trade in trades:
        verify_record(trade)
    journal = TradeJournal(VERSION, trades, "")
    return replace(journal, journal_hash=_hash(_journal_payload(journal)))


def verify_journal(journal: TradeJournal) -> bool:
    if journal.version != VERSION:
        raise JournalError("unsupported journal version")
    if tuple(sorted(journal.trades, key=lambda item: item.entry.trade_id)) != journal.trades:
        raise JournalError("journal trades must be sorted")
    if len({item.entry.trade_id for item in journal.trades}) != len(journal.trades):
        raise JournalError("duplicate trade IDs detected")
    for trade in journal.trades:
        verify_record(trade)
    clean = replace(journal, journal_hash="")
    if journal.journal_hash != _hash(_journal_payload(clean)):
        raise JournalError("journal hash mismatch")
    return True


def save_journal(journal: TradeJournal, path: str | Path) -> Path:
    verify_journal(journal)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_journal_payload(journal, include_hash=True), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def load_journal(path: str | Path) -> TradeJournal:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    trades = []
    for item in payload["trades"]:
        entry_data = item["entry"]
        entry = TradeEntry(
            trade_id=entry_data["trade_id"],
            symbol=entry_data["symbol"],
            direction=entry_data["direction"],
            entry_time=entry_data["entry_time"],
            entry_price=_d(entry_data["entry_price"]),
            quantity=_d(entry_data["quantity"]),
            signal_reason=entry_data["signal_reason"],
            signal_snapshot=_normalize_snapshot(entry_data["signal_snapshot"]),
            indicator_snapshot=_normalize_snapshot(entry_data["indicator_snapshot"]),
            portfolio_snapshot=_normalize_snapshot(entry_data["portfolio_snapshot"]),
            entry_commission=_d(entry_data["entry_commission"]),
            entry_slippage=_d(entry_data["entry_slippage"]),
            tags=tuple(entry_data["tags"]),
        )
        trades.append(TradeRecord(
            version=item["version"],
            entry=entry,
            exit_time=item["exit_time"],
            exit_price=None if item["exit_price"] is None else _d(item["exit_price"]),
            exit_reason=item["exit_reason"],
            exit_commission=_d(item["exit_commission"]),
            exit_slippage=_d(item["exit_slippage"]),
            gross_pnl=_d(item["gross_pnl"]),
            net_pnl=_d(item["net_pnl"]),
            holding_seconds=int(item["holding_seconds"]),
            record_hash=item["record_hash"],
        ))

    journal = TradeJournal(
        version=payload["version"],
        trades=tuple(trades),
        journal_hash=payload["journal_hash"],
    )
    verify_journal(journal)
    return journal


def export_csv(journal: TradeJournal, path: str | Path) -> Path:
    verify_journal(journal)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "trade_id", "symbol", "direction", "entry_time", "entry_price",
            "quantity", "exit_time", "exit_price", "signal_reason",
            "exit_reason", "gross_pnl", "net_pnl", "holding_seconds",
            "entry_commission", "exit_commission", "entry_slippage",
            "exit_slippage", "tags", "record_hash",
        ])
        writer.writeheader()
        for trade in journal.trades:
            writer.writerow({
                "trade_id": trade.entry.trade_id,
                "symbol": trade.entry.symbol,
                "direction": trade.entry.direction,
                "entry_time": trade.entry.entry_time,
                "entry_price": trade.entry.entry_price,
                "quantity": trade.entry.quantity,
                "exit_time": trade.exit_time or "",
                "exit_price": trade.exit_price or "",
                "signal_reason": trade.entry.signal_reason,
                "exit_reason": trade.exit_reason or "",
                "gross_pnl": trade.gross_pnl,
                "net_pnl": trade.net_pnl,
                "holding_seconds": trade.holding_seconds,
                "entry_commission": trade.entry.entry_commission,
                "exit_commission": trade.exit_commission,
                "entry_slippage": trade.entry.entry_slippage,
                "exit_slippage": trade.exit_slippage,
                "tags": "|".join(trade.entry.tags),
                "record_hash": trade.record_hash,
            })
    return target


MARKET_DATA_API_CALLED = False
ACCOUNT_API_CALLED = False
NETWORK_ACCESSED = False
BROKER_API_CALLED = False
BROKER_ORDER_CREATED = False
ORDER_SUBMITTED = False
LIVE_EXECUTION_AUTHORIZED = False
FUNDS_RESERVED = False
HOLDINGS_RESERVED = False
