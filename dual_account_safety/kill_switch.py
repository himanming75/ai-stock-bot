from __future__ import annotations
from dataclasses import replace
from .registry import AccountRegistry


class KillSwitchManager:
    def __init__(self, registry: AccountRegistry) -> None:
        self.registry = registry
        self.global_kill_switch = False

    def activate_account(self, account_key: str) -> None:
        profile = self.registry.get(account_key)
        self.registry.replace(
            replace(
                profile,
                kill_switch_active=True,
            )
        )

    def deactivate_account(self, account_key: str) -> None:
        profile = self.registry.get(account_key)
        self.registry.replace(
            replace(
                profile,
                kill_switch_active=False,
            )
        )

    def activate_global(self) -> None:
        self.global_kill_switch = True
        for profile in self.registry.all():
            self.activate_account(profile.account_key)

    def status(self) -> dict:
        return {
            "global_kill_switch": self.global_kill_switch,
            "accounts": {
                profile.account_key: (
                    profile.kill_switch_active
                )
                for profile in self.registry.all()
            },
        }
