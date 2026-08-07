from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any


@dataclass
class OperatorState:
    runtime_status: str = "STOPPED"
    requested_mode: str = "PAPER"
    paper_broker: str = "ALPACA"
    live_broker: str = "ETRADE"
    live_write_enabled: bool = False
    live_cancel_enabled: bool = False
    live_allocation_enabled: bool = False
    emergency_stop: bool = False
    last_action: str = "INITIALIZED"
    updated_at_utc: str = ""

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        if not result["updated_at_utc"]:
            result["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
        return result


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.save(OperatorState())

    def load(self) -> OperatorState:
        with self._lock:
            try:
                data = json.loads(
                    self.path.read_text(encoding="utf-8-sig")
                )
            except (OSError, json.JSONDecodeError):
                return OperatorState()
            return OperatorState(
                runtime_status=str(data.get("runtime_status", "STOPPED")),
                requested_mode=str(data.get("requested_mode", "PAPER")),
                paper_broker="ALPACA",
                live_broker="ETRADE",
                live_write_enabled=False,
                live_cancel_enabled=False,
                live_allocation_enabled=False,
                emergency_stop=bool(data.get("emergency_stop", False)),
                last_action=str(data.get("last_action", "RECOVERED")),
                updated_at_utc=str(data.get("updated_at_utc", "")),
            )

    def save(self, state: OperatorState) -> None:
        with self._lock:
            state.paper_broker = "ALPACA"
            state.live_broker = "ETRADE"
            state.live_write_enabled = False
            state.live_cancel_enabled = False
            state.live_allocation_enabled = False
            state.updated_at_utc = datetime.now(timezone.utc).isoformat()
            self.path.write_text(
                json.dumps(
                    state.to_dict(),
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )

    def apply_action(self, action: str) -> OperatorState:
        state = self.load()
        action = action.upper()

        if action == "EMERGENCY_STOP":
            state.emergency_stop = True
            state.runtime_status = "STOPPED"
            state.last_action = action
        elif action == "RESET_EMERGENCY_STOP":
            state.emergency_stop = False
            state.runtime_status = "STOPPED"
            state.last_action = action
        elif state.emergency_stop:
            state.last_action = "BLOCKED_BY_EMERGENCY_STOP"
        elif action == "START":
            state.runtime_status = "RUNNING"
            state.requested_mode = "PAPER"
            state.last_action = action
        elif action == "PAUSE":
            state.runtime_status = "PAUSED"
            state.last_action = action
        elif action == "RESUME":
            state.runtime_status = "RUNNING"
            state.requested_mode = "PAPER"
            state.last_action = action
        elif action == "STOP":
            state.runtime_status = "STOPPED"
            state.last_action = action
        else:
            state.last_action = "UNKNOWN_ACTION"

        self.save(state)
        return state
