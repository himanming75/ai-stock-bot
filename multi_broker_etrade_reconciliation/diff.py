from __future__ import annotations
from decimal import Decimal
from .models import ChangeEvent
from .severity import severity_for


def D(value) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def keyed(items: list[dict], *fields: str) -> dict[tuple, dict]:
    result = {}
    for item in items:
        key = tuple(str(item.get(field) or "") for field in fields)
        result[key] = item
    return result


def account_changes(previous: list[dict], current: list[dict]) -> list[ChangeEvent]:
    events = []
    before = keyed(previous, "account_id")
    after = keyed(current, "account_id")

    for key in sorted(set(before) | set(after)):
        old = before.get(key)
        new = after.get(key)
        account_id = key[0]

        if old is None:
            events.append(ChangeEvent(
                "ACCOUNT_ADDED", "INFO", "ACCOUNT", account_id,
                account_id, None, None, new, None,
                f"Account added: {account_id}",
            ))
            continue

        if new is None:
            events.append(ChangeEvent(
                "ACCOUNT_REMOVED", "WARNING", "ACCOUNT", account_id,
                account_id, None, old, None, None,
                f"Account removed: {account_id}",
            ))
            continue

        for field, event_type in (
            ("equity", "ACCOUNT_EQUITY_CHANGED"),
            ("cash", "ACCOUNT_CASH_CHANGED"),
            ("buying_power", "ACCOUNT_BUYING_POWER_CHANGED"),
        ):
            old_value = D(old.get(field))
            new_value = D(new.get(field))
            if old_value != new_value:
                delta = new_value - old_value
                events.append(ChangeEvent(
                    event_type,
                    severity_for(event_type, delta),
                    "ACCOUNT",
                    account_id,
                    account_id,
                    None,
                    str(old_value),
                    str(new_value),
                    str(delta),
                    f"{field} changed for {account_id}",
                ))

        old_status = str(old.get("status") or "UNKNOWN").upper()
        new_status = str(new.get("status") or "UNKNOWN").upper()
        if old_status != new_status:
            event_type = (
                "ACCOUNT_STATUS_CHANGED_TO_RESTRICTED"
                if new_status in {"RESTRICTED", "BLOCKED", "SUSPENDED"}
                else "ACCOUNT_STATUS_CHANGED"
            )
            events.append(ChangeEvent(
                event_type,
                severity_for(event_type),
                "ACCOUNT",
                account_id,
                account_id,
                None,
                old_status,
                new_status,
                None,
                f"Account status changed for {account_id}",
            ))

    return events


def position_changes(previous: list[dict], current: list[dict]) -> list[ChangeEvent]:
    events = []
    before = keyed(previous, "account_id", "symbol")
    after = keyed(current, "account_id", "symbol")

    for key in sorted(set(before) | set(after)):
        old = before.get(key)
        new = after.get(key)
        account_id, symbol = key
        entity_key = f"{account_id}:{symbol}"

        if old is None:
            events.append(ChangeEvent(
                "POSITION_OPENED",
                "WARNING",
                "POSITION",
                entity_key,
                account_id,
                symbol,
                None,
                new,
                str(D(new.get("quantity"))),
                f"Position opened: {entity_key}",
            ))
            continue

        if new is None:
            events.append(ChangeEvent(
                "POSITION_CLOSED",
                "WARNING",
                "POSITION",
                entity_key,
                account_id,
                symbol,
                old,
                None,
                str(-D(old.get("quantity"))),
                f"Position closed: {entity_key}",
            ))
            continue

        for field, event_type in (
            ("quantity", "POSITION_QUANTITY_CHANGED"),
            ("average_price", "POSITION_AVERAGE_PRICE_CHANGED"),
            ("market_value", "POSITION_MARKET_VALUE_CHANGED"),
            ("unrealized_pl", "POSITION_UNREALIZED_PL_CHANGED"),
        ):
            old_value = D(old.get(field))
            new_value = D(new.get(field))
            if old_value != new_value:
                delta = new_value - old_value
                events.append(ChangeEvent(
                    event_type,
                    severity_for(event_type, delta),
                    "POSITION",
                    entity_key,
                    account_id,
                    symbol,
                    str(old_value),
                    str(new_value),
                    str(delta),
                    f"{field} changed for {entity_key}",
                ))

    return events


def order_changes(previous: list[dict], current: list[dict]) -> list[ChangeEvent]:
    events = []
    before = keyed(previous, "account_id", "order_id")
    after = keyed(current, "account_id", "order_id")

    for key in sorted(set(before) | set(after)):
        old = before.get(key)
        new = after.get(key)
        account_id, order_id = key
        symbol = str((new or old or {}).get("symbol") or "")
        entity_key = f"{account_id}:{order_id}"

        if old is None:
            events.append(ChangeEvent(
                "ORDER_ADDED",
                "INFO",
                "ORDER",
                entity_key,
                account_id,
                symbol,
                None,
                new,
                None,
                f"Order added: {entity_key}",
            ))
            continue

        if new is None:
            events.append(ChangeEvent(
                "ORDER_REMOVED",
                "WARNING",
                "ORDER",
                entity_key,
                account_id,
                symbol,
                old,
                None,
                None,
                f"Order removed: {entity_key}",
            ))
            continue

        old_status = str(old.get("status") or "UNKNOWN").upper()
        new_status = str(new.get("status") or "UNKNOWN").upper()
        if old_status != new_status:
            events.append(ChangeEvent(
                "ORDER_STATUS_CHANGED",
                "WARNING",
                "ORDER",
                entity_key,
                account_id,
                symbol,
                old_status,
                new_status,
                None,
                f"Order status changed: {old_status} -> {new_status}",
            ))

        old_filled = D(old.get("filled_quantity"))
        new_filled = D(new.get("filled_quantity"))
        if old_filled != new_filled:
            events.append(ChangeEvent(
                "ORDER_FILLED_QUANTITY_CHANGED",
                "INFO",
                "ORDER",
                entity_key,
                account_id,
                symbol,
                str(old_filled),
                str(new_filled),
                str(new_filled - old_filled),
                f"Filled quantity changed for {entity_key}",
            ))

    return events
