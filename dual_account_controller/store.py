from __future__ import annotations
import json
from pathlib import Path

from .models import ControllerState


class ControllerStateStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def save(self, state: ControllerState) -> None:
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self.path.write_text(
            json.dumps(
                state.to_dict(),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def load(self) -> ControllerState:
        if not self.path.exists():
            return ControllerState(
                active_profile="ALL_STOP",
                profile_locked=False,
                global_kill_switch=True,
                account_kill_switches={
                    "ALPACA_PAPER_PRIMARY": True,
                    "ETRADE_PRIMARY": True,
                },
                last_transition_reason="DEFAULT_SAFE_STATE",
                last_transition_status="RESTORED_DEFAULT",
                sequence=0,
            )

        payload = json.loads(
            self.path.read_text(
                encoding="utf-8-sig"
            )
        )
        return ControllerState(
            active_profile=str(
                payload.get(
                    "active_profile",
                    "ALL_STOP",
                )
            ).upper(),
            profile_locked=bool(
                payload.get(
                    "profile_locked",
                    False,
                )
            ),
            global_kill_switch=bool(
                payload.get(
                    "global_kill_switch",
                    True,
                )
            ),
            account_kill_switches={
                str(key): bool(value)
                for key, value in dict(
                    payload.get(
                        "account_kill_switches",
                        {},
                    )
                ).items()
            },
            last_transition_reason=str(
                payload.get(
                    "last_transition_reason",
                    "UNKNOWN",
                )
            ),
            last_transition_status=str(
                payload.get(
                    "last_transition_status",
                    "UNKNOWN",
                )
            ),
            sequence=int(
                payload.get(
                    "sequence",
                    0,
                )
            ),
        )
