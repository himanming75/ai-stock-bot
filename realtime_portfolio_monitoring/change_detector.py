from __future__ import annotations

import json
from pathlib import Path

from .models import decimal_value


def load_previous_snapshot(
    path: Path,
) -> dict | None:
    if not path.exists():
        return None
    return json.loads(
        path.read_text(encoding="utf-8-sig")
    )


def detect_position_changes(
    previous: dict | None,
    current_positions: list[dict],
) -> list[dict]:
    if not previous:
        return [
            {
                "symbol": item["symbol"],
                "change_type": "INITIAL_POSITION",
                "previous_qty": "0",
                "current_qty": item["qty"],
            }
            for item in current_positions
        ]

    previous_positions = {
        item["symbol"]: item
        for item in previous.get("positions", [])
    }
    current_map = {
        item["symbol"]: item
        for item in current_positions
    }

    changes = []
    for symbol in sorted(
        set(previous_positions) | set(current_map)
    ):
        previous_qty = decimal_value(
            previous_positions.get(
                symbol, {}
            ).get("qty")
        )
        current_qty = decimal_value(
            current_map.get(symbol, {}).get("qty")
        )

        if previous_qty == current_qty:
            continue

        if previous_qty == 0 and current_qty != 0:
            change_type = "POSITION_OPENED"
        elif previous_qty != 0 and current_qty == 0:
            change_type = "POSITION_CLOSED"
        elif abs(current_qty) > abs(previous_qty):
            change_type = "POSITION_INCREASED"
        else:
            change_type = "POSITION_DECREASED"

        changes.append(
            {
                "symbol": symbol,
                "change_type": change_type,
                "previous_qty": str(previous_qty),
                "current_qty": str(current_qty),
                "quantity_delta": str(
                    current_qty - previous_qty
                ),
            }
        )
    return changes
